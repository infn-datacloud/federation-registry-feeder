import copy
from concurrent.futures import ThreadPoolExecutor

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
from pydantic import AnyHttpUrl

from src.logger import create_logger
from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Kubernetes, Openstack, Project
from src.providers.conn_thread import ConnectionThread
from src.providers.openstack import OpenstackProviderException


class ProviderThread:
    """Provider data shared between the same thread."""

    def __init__(
        self,
        *,
        provider_conf: Openstack | Kubernetes,
        issuers: list[Issuer],
        log_level: str | int | None = None,
    ) -> None:
        self.provider_conf = provider_conf
        self.issuers = issuers
        self.log_level = log_level
        self.logger = create_logger(
            f"Provider {self.provider_conf.name}", level=log_level
        )
        self.error = False

    def prepare_project_conf(self, *, project: Project, region_name: str) -> Project:
        """Get project parameters defined in the yaml file.

        If the `per_region_props` attribute has been defined and the current region name
        matches the name of the region definining the new props, override project's
        corresponding values.
        """
        # Find region props matching current region.
        region_props = filter(
            lambda x: x.region_name == region_name, project.per_region_props
        )
        region_props = next(region_props, None)

        item = Project(**project.dict(exclude={"per_region_props"}))
        if region_props:
            item.default_private_net = region_props.default_private_net
            item.default_public_net = region_props.default_public_net
            item.private_net_proxy = region_props.private_net_proxy
            item.per_user_limits = region_props.per_user_limits
        return item

    def get_issuer_matching_project(self, project_sla: str) -> Issuer:
        """Find the identity provider with an SLA matching the target project's one.

        For each sla of each user group of each issuer listed in the yaml file, find the
        one matching the SLA of the target project.

        Return the indentity provider data and the token to use to establish the
        connection.
        """
        for issuer in self.issuers:
            for user_group in issuer.user_groups:
                for sla in user_group.slas:
                    if sla.doc_uuid == project_sla:
                        return Issuer(
                            **issuer.dict(by_alias=True, exclude={"user_groups"}),
                            user_groups=[
                                {
                                    **user_group.dict(exclude={"slas"}),
                                    "slas": [{**sla.dict()}],
                                }
                            ],
                        )
        raise ValueError(f"No SLA matches project's doc_uuid `{project_sla}`")

    def get_auth_method_matching_issuer(
        self, issuer_endpoint: AnyHttpUrl
    ) -> AuthMethod:
        for auth_method in self.provider_conf.identity_providers:
            if auth_method.endpoint == issuer_endpoint:
                return auth_method
        trusted_endpoints = [i.endpoint for i in self.provider_conf.identity_providers]
        raise ValueError(
            f"No identity provider matches endpoint `{issuer_endpoint}` in "
            f"provider's trusted identity providers {trusted_endpoints}."
        )

    def get_updated_identity_provider(
        self,
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
        self,
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

    def get_updated_services(
        self,
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
                    if isinstance(
                        service,
                        (
                            BlockStorageServiceCreateExtended,
                            ComputeServiceCreateExtended,
                            NetworkServiceCreateExtended,
                            ObjectStoreServiceCreateExtended,
                        ),
                    ):
                        service.quotas += new_service.quotas
                    if isinstance(service, ComputeServiceCreateExtended):
                        service.flavors = self.get_updated_resources(
                            current_resources=service.flavors,
                            new_resources=new_service.flavors,
                        )
                        service.images = self.get_updated_resources(
                            current_resources=service.images,
                            new_resources=new_service.images,
                        )
                    if isinstance(service, NetworkServiceCreateExtended):
                        service.networks = self.get_updated_resources(
                            current_resources=service.networks,
                            new_resources=new_service.networks,
                        )
                    break
            else:
                current_services.append(new_service)
        return current_services

    def get_updated_region(
        self,
        *,
        current_region: RegionCreateExtended | None,
        new_region: RegionCreateExtended,
    ) -> RegionCreateExtended:
        """Update region services."""
        if current_region is None:
            return new_region
        current_region.block_storage_services = self.get_updated_services(
            current_services=current_region.block_storage_services,
            new_services=new_region.block_storage_services,
        )
        current_region.compute_services = self.get_updated_services(
            current_services=current_region.compute_services,
            new_services=new_region.compute_services,
        )
        current_region.identity_services = self.get_updated_services(
            current_services=current_region.identity_services,
            new_services=new_region.identity_services,
        )
        current_region.network_services = self.get_updated_services(
            current_services=current_region.network_services,
            new_services=new_region.network_services,
        )
        current_region.object_store_services = self.get_updated_services(
            current_services=current_region.object_store_services,
            new_services=new_region.object_store_services,
        )
        return current_region

    def filter_compute_resources_projects(
        self,
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

    def merge_data(
        self,
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
            identity_providers[
                identity_provider.endpoint
            ] = self.get_updated_identity_provider(
                current_idp=identity_providers.get(identity_provider.endpoint),
                new_idp=identity_provider,
            )
            regions[region.name] = self.get_updated_region(
                current_region=regions.get(region.name), new_region=region
            )

        # Filter non-federated projects from shared resources
        for region in regions.values():
            for service in region.compute_services:
                service.flavors = self.filter_compute_resources_projects(
                    items=service.flavors, projects=projects.keys()
                )
                service.images = self.filter_compute_resources_projects(
                    items=service.images, projects=projects.keys()
                )

        return (
            list(identity_providers.values()),
            list(projects.values()),
            list(regions.values()),
        )

    def get_provider(self) -> ProviderCreateExtended:
        """Generate a list of generic providers.

        Read data from real instances.
        Supported providers:
        - Openstack
        """
        if self.provider_conf.status != ProviderStatus.ACTIVE.value:
            self.logger.info("Provider not active: %s", self.provider_conf.status)
            return ProviderCreateExtended(
                name=self.provider_conf.name,
                type=self.provider_conf.type,
                is_public=self.provider_conf.is_public,
                support_emails=self.provider_conf.support_emails,
                status=self.provider_conf.status,
            )

        # For each couple (region-project), create a separated thread and try to connect
        # to the provider
        connections: list[ConnectionThread] = []
        for region in self.provider_conf.regions:
            for project in self.provider_conf.projects:
                try:
                    project_conf = self.prepare_project_conf(
                        project=project, region_name=region.name
                    )
                    issuer = self.get_issuer_matching_project(project_conf.sla)
                    auth_method = self.get_auth_method_matching_issuer(issuer.endpoint)
                    provider_conf = copy.deepcopy(self.provider_conf)
                    provider_conf.regions = [region]
                    provider_conf.projects = [project_conf]
                    provider_conf.identity_providers = [auth_method]
                    connections.append(
                        ConnectionThread(
                            provider_conf=provider_conf,
                            issuer=issuer,
                            log_level=self.log_level,
                        )
                    )
                except (
                    OpenstackProviderException,
                    NotImplementedError,
                    ValueError,
                    AssertionError,
                ) as e:
                    self.error = True
                    self.logger.error(e)
                    self.logger.error("Skipping project")

        with ThreadPoolExecutor() as executor:
            siblings = executor.map(lambda x: x.get_provider_components(), connections)
        siblings = list(siblings)
        self.error |= any([x.error for x in connections])

        # Merge regions, identity providers and projects retrieved from previous
        # parallel step.
        identity_providers, projects, regions = self.merge_data(siblings)

        return ProviderCreateExtended(
            name=self.provider_conf.name,
            type=self.provider_conf.type,
            is_public=self.provider_conf.is_public,
            support_emails=self.provider_conf.support_emails,
            status=ProviderStatus.LIMITED if self.error else self.provider_conf.status,
            identity_providers=identity_providers,
            projects=projects,
            regions=regions,
        )
