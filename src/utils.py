import os
from concurrent.futures import ThreadPoolExecutor
from logging import Logger

import yaml
from fed_reg.provider.enum import ProviderStatus
from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityProviderCreateExtended,
    ImageCreateExtended,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
    RegionCreateExtended,
)
from liboidcagent.liboidcagent import OidcAgentConnectError, OidcAgentError
from pydantic import ValidationError

from src.logger import create_logger
from src.models.config import Settings, URLs
from src.models.provider import Kubernetes, Openstack
from src.models.site_config import SiteConfig
from src.providers.openstack import OpenstackData


def infer_service_endpoints(*, settings: Settings, logger: Logger) -> URLs:
    """Detect Federation-Registry endpoints from given configuration."""
    logger.info("Building Federation-Registry endpoints from configuration.")
    logger.debug("%r", settings)
    d = {}
    for k, v in settings.api_ver.dict().items():
        d[k.lower()] = os.path.join(settings.FED_REG_API_URL, f"{v}", f"{k.lower()}")
    endpoints = URLs(**d)
    logger.info("Federation-Registry endpoints detected")
    logger.debug("%r", endpoints)
    return endpoints


def get_conf_files(*, settings: Settings, logger: Logger) -> list[str]:
    """Get the list of the yaml files with the provider configurations."""
    logger.info("Detecting yaml files with provider configurations.")
    file_extension = ".config.yaml"
    try:
        yaml_files = filter(
            lambda x: x.endswith(file_extension),
            os.listdir(settings.PROVIDERS_CONF_DIR),
        )
        yaml_files = [os.path.join(settings.PROVIDERS_CONF_DIR, i) for i in yaml_files]
        logger.info("Files retrieved")
        logger.debug(yaml_files)
    except FileNotFoundError as e:
        logger.error(e)
        yaml_files = []
    return yaml_files


def load_config(*, fname: str, log_level: str | int | None = None) -> SiteConfig | None:
    """Load provider configuration from yaml file."""
    logger = create_logger(f"Yaml file {fname}", level=log_level)
    logger.info("Loading provider configuration from file")

    try:
        with open(fname) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError as e:
        logger.error(e)
        return None

    if config:
        try:
            config = SiteConfig(**config)
            logger.info("Configuration loaded")
            logger.debug("%r", config)
            return config
        except (ValidationError, OidcAgentConnectError, OidcAgentError) as e:
            logger.error(e)
            return None
    else:
        logger.error("Empty configuration")
        return config


def get_site_configs(
    *, yaml_files: list[str], log_level: str | int | None = None
) -> tuple[list[SiteConfig], bool]:
    """Create a list of SiteConfig from a list of yaml files."""
    with ThreadPoolExecutor() as executor:
        site_configs = executor.map(
            lambda x: load_config(fname=x, log_level=log_level), yaml_files
        )
    site_configs = list(site_configs)
    error = any([x is None for x in site_configs])
    items = list(filter(lambda x: x is not None, site_configs))
    return items, error


def filter_compute_resources_projects(
    *,
    items: list[FlavorCreateExtended] | list[ImageCreateExtended],
    projects: list[str],
) -> list[FlavorCreateExtended] | list[ImageCreateExtended]:
    """Remove from compute resources projects not imported in the Fed-Reg.

    Apply the filtering only on private flavors and images.

    Since resources not matching at least the project used to discover them have
    already been discarded, on a specific resource, after the filtering projects,
    there can't be an empty projects list.
    """
    for item in items:
        if not item.is_public:
            item.projects = list(
                filter(lambda x, projects=projects: x in projects, item.projects)
            )
    return items


def get_updated_identity_provider(
    *,
    current_idp: IdentityProviderCreateExtended | None,
    new_idp: IdentityProviderCreateExtended,
) -> IdentityProviderCreateExtended:
    """
    Update the identity provider user groups.

    Since for each provider a user group can have just one SLA pointing to exactly
    one project. If the user group is not already in the current identity provider
    user groups add it, otherwise skip.
    """
    if current_idp is None:
        return new_idp
    names = [i.name for i in current_idp.user_groups]
    if new_idp.user_groups[0].name not in names:
        current_idp.user_groups.append(new_idp.user_groups[0])
    return current_idp


def get_updated_resources(
    *,
    current_resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkServiceCreateExtended],
    new_resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkServiceCreateExtended],
) -> (
    list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkServiceCreateExtended]
):
    """Update Compute services.

    If the service does not exist, add it; otherwise, add new quotas, flavors and
    images.
    """
    curr_uuids = [i.uuid for i in current_resources]
    current_resources += list(
        filter(lambda x, uuids=curr_uuids: x.uuid not in uuids, new_resources)
    )
    return current_resources


def update_service(
    *,
    curr_service: BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | NetworkServiceCreateExtended
    | ObjectStoreServiceCreateExtended,
    new_service: BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | NetworkServiceCreateExtended
    | ObjectStoreServiceCreateExtended,
) -> (
    BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | NetworkServiceCreateExtended
    | ObjectStoreServiceCreateExtended
):
    if isinstance(
        curr_service,
        (
            BlockStorageServiceCreateExtended,
            ComputeServiceCreateExtended,
            NetworkServiceCreateExtended,
            ObjectStoreServiceCreateExtended,
        ),
    ):
        curr_service.quotas += new_service.quotas
    if isinstance(curr_service, ComputeServiceCreateExtended):
        curr_service.flavors = get_updated_resources(
            current_resources=curr_service.flavors,
            new_resources=new_service.flavors,
        )
        curr_service.images = get_updated_resources(
            current_resources=curr_service.images,
            new_resources=new_service.images,
        )
    if isinstance(curr_service, NetworkServiceCreateExtended):
        curr_service.networks = get_updated_resources(
            current_resources=curr_service.networks,
            new_resources=new_service.networks,
        )
    return curr_service


def get_updated_services(
    *,
    current_services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
    new_services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> (
    list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended]
):
    """Update Object store services.

    If the service does not exist, add it; otherwise, add new quotas and resources.
    """
    for new_service in new_services:
        for service in current_services:
            if service.endpoint == new_service.endpoint:
                service = update_service(curr_service=service, new_service=new_service)
                break
        else:
            current_services.append(new_service)
    return current_services


def get_updated_region(
    *,
    current_region: RegionCreateExtended | None,
    new_region: RegionCreateExtended,
) -> RegionCreateExtended:
    """Update region services."""
    if current_region is None:
        return new_region
    current_region.block_storage_services = get_updated_services(
        current_services=current_region.block_storage_services,
        new_services=new_region.block_storage_services,
    )
    current_region.compute_services = get_updated_services(
        current_services=current_region.compute_services,
        new_services=new_region.compute_services,
    )
    current_region.identity_services = get_updated_services(
        current_services=current_region.identity_services,
        new_services=new_region.identity_services,
    )
    current_region.network_services = get_updated_services(
        current_services=current_region.network_services,
        new_services=new_region.network_services,
    )
    current_region.object_store_services = get_updated_services(
        current_services=current_region.object_store_services,
        new_services=new_region.object_store_services,
    )
    return current_region


def merge_components(
    siblings: list[
        tuple[IdentityProviderCreateExtended, ProjectCreate, RegionCreateExtended]
    ],
) -> tuple[
    list[IdentityProviderCreateExtended],
    list[ProjectCreate],
    list[RegionCreateExtended],
]:
    """Merge regions, identity providers and projects."""
    identity_providers: dict[str, IdentityProviderCreateExtended] = {}
    projects: dict[str, ProjectCreate] = {}
    regions: dict[str, RegionCreateExtended] = {}

    for identity_provider, project, region in siblings:
        projects[project.uuid] = project
        identity_providers[identity_provider.endpoint] = get_updated_identity_provider(
            current_idp=identity_providers.get(identity_provider.endpoint),
            new_idp=identity_provider,
        )
        regions[region.name] = get_updated_region(
            current_region=regions.get(region.name), new_region=region
        )

    # Filter non-federated projects from shared resources
    for region in regions.values():
        for service in region.compute_services:
            service.flavors = filter_compute_resources_projects(
                items=service.flavors, projects=projects.keys()
            )
            service.images = filter_compute_resources_projects(
                items=service.images, projects=projects.keys()
            )

    return (
        list(identity_providers.values()),
        list(projects.values()),
        list(regions.values()),
    )


def retrieve_components(
    data: OpenstackData,
) -> tuple[IdentityProviderCreateExtended, ProjectCreate, RegionCreateExtended] | None:
    region = RegionCreateExtended(
        **data.provider_conf.regions[0].dict(),
        block_storage_services=data.block_storage_services,
        compute_services=data.compute_services,
        identity_services=data.identity_services,
        network_services=data.network_services,
        object_store_services=data.object_store_services,
    )
    identity_provider = IdentityProviderCreateExtended(
        description=data.issuer.description,
        group_claim=data.issuer.group_claim,
        endpoint=data.issuer.endpoint,
        relationship=data.provider_conf.identity_providers[0],
        user_groups=[
            {
                **data.issuer.user_groups[0].dict(exclude={"slas"}),
                "sla": {
                    **data.issuer.user_groups[0].slas[0].dict(),
                    "project": data.provider_conf.projects[0].id,
                },
            }
        ],
    )
    return identity_provider, data.project, region


def create_provider(
    *,
    provider_conf: Openstack | Kubernetes,
    connections_data: list[OpenstackData],
    error: bool,
) -> ProviderCreateExtended:
    """Merge regions, identity providers and projects retrieved from previous steps."""
    siblings = [retrieve_components(data) for data in connections_data]
    identity_providers, projects, regions = merge_components(siblings)
    return ProviderCreateExtended(
        name=provider_conf.name,
        type=provider_conf.type,
        is_public=provider_conf.is_public,
        support_emails=provider_conf.support_emails,
        status=ProviderStatus.LIMITED if error else provider_conf.status,
        identity_providers=identity_providers,
        projects=projects,
        regions=regions,
    )
