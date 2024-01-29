import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List, Optional, Tuple

from app.provider.enum import ProviderStatus, ProviderType
from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
    RegionCreateExtended,
    SLACreateExtended,
    UserGroupCreateExtended,
)

from src.logger import logger
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import AuthMethod, PerRegionProps, Project, Provider
from src.providers.openstack import get_data_from_openstack

projects_lock = Lock()
region_lock = Lock()
issuer_lock = Lock()


def filter_projects_on_compute_resources(
    *, region: RegionCreateExtended, include_projects: List[str]
) -> None:
    """Remove from compute resources projects not imported in the Federation-Registry"""
    for service in region.compute_services:
        for flavor in service.flavors:
            flavor.projects = list(
                filter(lambda x: x in include_projects, flavor.projects)
            )
        for image in service.images:
            image.projects = list(
                filter(lambda x: x in include_projects, image.projects)
            )


def get_identity_provider_info_for_project(
    *, issuers: List[Issuer], auth_methods: List[AuthMethod], project: Project
) -> Tuple[IdentityProviderCreateExtended, str]:
    """Find the identity provider with an SLA matching the one of target project.

    For each sla of each user group of each issuer listed in the yaml file, find the one
    matching the SLA of the target project. Add project id to SLA's project list if not
    present.
    """
    for issuer in issuers:
        for user_group in issuer.user_groups:
            for sla in user_group.slas:
                if sla.doc_uuid == project.sla:
                    return get_identity_provider_with_auth_method(
                        auth_methods=auth_methods,
                        issuer=issuer,
                        user_group=user_group,
                        sla=sla,
                        project=project.id,
                    ), issuer.token
    raise ValueError(
        f"No SLA matching doc_uuid `{project.sla}` in project configuration"
    )


def get_identity_provider_with_auth_method(
    *,
    auth_methods: List[AuthMethod],
    issuer: Issuer,
    user_group: UserGroup,
    sla: SLA,
    project: str,
) -> IdentityProviderCreateExtended:
    for auth_method in auth_methods:
        if auth_method.endpoint == issuer.endpoint:
            sla = SLACreateExtended(**sla.dict(), project=project)
            user_group = UserGroupCreateExtended(
                description=user_group.description, name=user_group.name, sla=sla
            )
            return IdentityProviderCreateExtended(
                description=issuer.description,
                group_claim=issuer.group_claim,
                endpoint=issuer.endpoint,
                relationship=auth_method,
                user_groups=[user_group],
            )
    raise ValueError(
        f"No identity provider matching endpoint `{issuer.endpoint}` in provider "
        f"trusted identity providers {[i.endpoint for i in auth_methods]}"
    )


def get_project_conf_params(
    *, project_conf: Project, region_props: Optional[PerRegionProps] = None
) -> Project:
    """Get project parameters defined in the yaml file.

    If the `per_region` attribute has been defined, override values if the region name
    matches the current region.
    """
    new_conf = Project(**project_conf.dict(exclude={"per_region_props"}))
    if region_props:
        new_conf.default_private_net = region_props.default_private_net
        new_conf.default_public_net = region_props.default_public_net
        new_conf.private_net_proxy = region_props.private_net_proxy
        new_conf.per_user_limits = region_props.per_user_limits
    return new_conf


def update_identity_providers(
    *,
    current_issuers: List[IdentityProviderCreateExtended],
    new_issuer: IdentityProviderCreateExtended,
) -> None:
    try:
        idx = [i.endpoint for i in current_issuers].index(new_issuer.endpoint)
    except ValueError:
        idx = -1

    if idx == -1:
        current_issuers.append(new_issuer)
    else:
        # Add new user group since for each provider a user group can have just one SLA
        # pointing to one project.
        current_issuers[idx].user_groups.append(new_issuer.user_groups[0])


def update_region_block_storage_services(
    *,
    current_services: List[BlockStorageServiceCreateExtended],
    new_service: BlockStorageServiceCreateExtended,
) -> None:
    for service in current_services:
        if service.endpoint == new_service.endpoint:
            service.quotas += new_service.quotas
            break
    else:
        current_services.append(new_service)


def update_region_compute_services(
    *,
    current_services: List[ComputeServiceCreateExtended],
    new_service: ComputeServiceCreateExtended,
) -> None:
    for service in current_services:
        if service.endpoint == new_service.endpoint:
            curr_uuids = [i.uuid for i in service.flavors]
            service.flavors += list(
                filter(
                    lambda x, uuids=curr_uuids: x.uuid not in uuids,
                    new_service.flavors,
                )
            )
            curr_uuids = [i.uuid for i in service.images]
            service.images += list(
                filter(
                    lambda x, uuids=curr_uuids: x.uuid not in uuids,
                    new_service.images,
                )
            )
            service.quotas += new_service.quotas
            break
    else:
        current_services.append(new_service)


def update_region_identity_services(
    *, current_services: List[IdentityServiceCreate], new_service: IdentityServiceCreate
) -> None:
    for service in current_services:
        if service.endpoint == new_service.endpoint:
            break
    else:
        current_services.append(new_service)


def update_region_network_services(
    *,
    current_services: List[NetworkServiceCreateExtended],
    new_service: NetworkServiceCreateExtended,
) -> None:
    for service in current_services:
        if service.endpoint == new_service.endpoint:
            curr_uuids = [i.uuid for i in service.networks]
            service.networks += list(
                filter(
                    lambda x, uuids=curr_uuids: x.uuid not in uuids,
                    new_service.networks,
                )
            )
            service.quotas += new_service.quotas
            break
    else:
        current_services.append(new_service)


def get_project_resources(
    *,
    provider_conf: Provider,
    project_conf: Project,
    issuers: List[Issuer],
    out_region: RegionCreateExtended,
    out_projects: List[ProjectCreate],
    out_issuers: List[IdentityProviderCreateExtended],
) -> None:
    # Find region props matching current region.
    region_props = next(
        filter(
            lambda x: x.region_name == out_region.name,
            project_conf.per_region_props,
        ),
        None,
    )
    proj_conf = get_project_conf_params(
        project_conf=project_conf, region_props=region_props
    )

    try:
        identity_provider, token = get_identity_provider_info_for_project(
            issuers=issuers,
            auth_methods=provider_conf.identity_providers,
            project=proj_conf,
        )
    except ValueError as e:
        logger.error(e)
        logger.error(f"Skipping project {proj_conf.id}.")
        return None

    if provider_conf.type == ProviderType.OS.value:
        resp = get_data_from_openstack(
            provider_conf=provider_conf,
            project_conf=proj_conf,
            identity_provider=identity_provider,
            token=token,
            region_name=out_region.name,
        )
    if provider_conf.type == ProviderType.K8S.value:
        # Not yet implemented
        resp = None
    if not resp:
        return None

    (
        project,
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    ) = resp
    with region_lock:
        update_region_block_storage_services(
            current_services=out_region.block_storage_services,
            new_service=block_storage_service,
        )
        update_region_compute_services(
            current_services=out_region.compute_services, new_service=compute_service
        )
        update_region_identity_services(
            current_services=out_region.identity_services, new_service=identity_service
        )
        update_region_network_services(
            current_services=out_region.network_services, new_service=network_service
        )

    with projects_lock:
        if project.uuid not in [i.uuid for i in out_projects]:
            out_projects.append(project)

    with issuer_lock:
        update_identity_providers(
            current_issuers=out_issuers, new_issuer=identity_provider
        )
    return None


def get_provider(
    *, os_conf: Provider, trusted_idps: List[Issuer]
) -> ProviderCreateExtended:
    """Generate an Openstack virtual provider, reading information from a real openstack
    instance.
    """
    if os_conf.status != ProviderStatus.ACTIVE.value:
        logger.info(f"Provider={os_conf.name} not active: {os_conf.status}")
        return ProviderCreateExtended(
            name=os_conf.name,
            type=os_conf.type,
            is_public=os_conf.is_public,
            support_emails=os_conf.support_emails,
            status=os_conf.status,
        )

    trust_idps = copy.deepcopy(trusted_idps)
    regions: List[RegionCreateExtended] = []
    projects: List[ProjectCreate] = []
    identity_providers: List[IdentityProviderCreateExtended] = []

    for region_conf in os_conf.regions:
        region = RegionCreateExtended(**region_conf.dict())
        thread_pool = ThreadPoolExecutor(max_workers=len(os_conf.projects))
        for project_conf in os_conf.projects:
            thread_pool.submit(
                get_project_resources,
                provider_conf=os_conf,
                project_conf=project_conf,
                issuers=trust_idps,
                out_region=region,
                out_projects=projects,
                out_issuers=identity_providers,
            )
        thread_pool.shutdown(wait=True)
        regions.append(region)

    # This should be done at the end since we could have skipped some project due to
    # lack of authorizations or misconfigurations.
    for region in regions:
        filter_projects_on_compute_resources(
            region=region, include_projects=[i.uuid for i in projects]
        )

    return ProviderCreateExtended(
        name=os_conf.name,
        type=os_conf.type,
        is_public=os_conf.is_public,
        support_emails=os_conf.support_emails,
        status=os_conf.status,
        identity_providers=identity_providers,
        projects=projects,
        regions=regions,
    )
