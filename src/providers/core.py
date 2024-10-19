import copy
from concurrent.futures import ThreadPoolExecutor

from fed_reg.provider.enum import ProviderStatus, ProviderType
from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    ImageCreateExtended,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
    RegionCreateExtended,
)

from src.kafka_conn import Producer
from src.logger import create_logger
from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Project, Provider, ProviderSiblings
from src.providers.openstack import OpenstackData, ProviderException


class ConnectionThread:
    """Data shared between the same connection socket"""

    def __init__(
        self,
        *,
        provider_conf: Provider,
        issuer: Issuer,
        log_level: str | int | None = None,
    ) -> None:
        assert (
            len(provider_conf.regions) == 1
        ), f"Invalid number or regions: {len(provider_conf.regions)}"
        assert (
            len(provider_conf.projects) == 1
        ), f"Invalid number or projects: {len(provider_conf.projects)}"
        msg = "Invalid number or trusted identity providers: "
        msg += f"{len(provider_conf.identity_providers)}"
        assert len(provider_conf.identity_providers) == 1, msg
        msg = f"Issuer endpoint {issuer.endpoint} does not match trusted identity "
        msg += f"provider's one {provider_conf.identity_providers[0].endpoint}"
        assert issuer.endpoint == provider_conf.identity_providers[0].endpoint, msg
        assert (
            len(issuer.user_groups) == 1
        ), f"Invalid number or user groups: {len(issuer.user_groups)}"
        assert (
            len(issuer.user_groups[0].slas) == 1
        ), f"Invalid number or user groups: {len(issuer.user_groups[0].slas)}"

        self.provider_conf = provider_conf
        self.region_name = provider_conf.regions[0].name
        self.issuer = issuer

        logger_name = f"Provider {provider_conf.name}, "
        logger_name += f"Region {provider_conf.regions[0].name}, "
        logger_name += f"Project {provider_conf.projects[0].id}"
        self.logger = create_logger(logger_name, level=log_level)

        self.error = False

    def get_provider_siblings(self) -> ProviderSiblings | None:
        """Retrieve the provider region, project and identity provider.

        From the current configuration, connect to the correct provider and retrieve the
        current configuration and resources.

        Return an object with 3 main entities: region, project and identity provider.
        """
        identity_provider = IdentityProviderCreateExtended(
            description=self.issuer.description,
            group_claim=self.issuer.group_claim,
            endpoint=self.issuer.endpoint,
            relationship=self.provider_conf.identity_providers[0],
            user_groups=[
                {
                    **self.issuer.user_groups[0].dict(exclude={"slas"}),
                    "sla": {
                        **self.issuer.user_groups[0].slas[0].dict(),
                        "project": self.provider_conf.projects[0].id,
                    },
                }
            ],
        )

        if self.provider_conf.type == ProviderType.OS.value:
            try:
                data = OpenstackData(
                    provider_conf=self.provider_conf,
                    project_conf=self.provider_conf.projects[0],
                    region_name=self.region_name,
                    auth_method=self.provider_conf.identity_providers[0],
                    token=self.issuer.token,
                    logger=self.logger,
                )
                self.error |= data.error
            except ProviderException:
                self.error = True
                return None
        elif self.provider_conf.type == ProviderType.K8S.value:
            self.logger.warning("Not yet implemented")
            self.logger.warning("Skipping project")
            return None

        region = RegionCreateExtended(
            **self.provider_conf.regions[0].dict(),
            block_storage_services=[data.block_storage_service]
            if data.block_storage_service
            else [],
            compute_services=[data.compute_service] if data.compute_service else [],
            identity_services=[data.identity_service] if data.identity_service else [],
            network_services=[data.network_service] if data.network_service else [],
            object_store_services=data.object_store_services,
        )

        return ProviderSiblings(
            identity_provider=identity_provider, project=data.project, region=region
        )


class ProviderThread:
    """Provider data shared between the same thread."""

    def __init__(
        self,
        *,
        provider_conf: Provider,
        issuers: list[Issuer],
        kafka_prod: Producer | None = None,
        log_level: str | int | None = None,
    ) -> None:
        self.provider_conf = provider_conf
        self.issuers = issuers
        self.kafka_prod = kafka_prod
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

    def get_issuer_matching_project(
        self, *, issuers: list[Issuer], project_sla: str
    ) -> Issuer:
        """Find the identity provider with an SLA matching the target project's one.

        For each sla of each user group of each issuer listed in the yaml file, find the
        one matching the SLA of the target project.

        Return the indentity provider data and the token to use to establish the
        connection.
        """
        for issuer in issuers:
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
        raise ValueError(
            f"No SLA matches project's doc_uuid `{self.provider_conf.projects[0].sla}`"
        )

    def get_auth_method_matching_issuer(
        self, *, provider_auth_methods: list[AuthMethod], issuer_endpoint
    ) -> AuthMethod:
        for auth_method in provider_auth_methods:
            if auth_method.endpoint == issuer_endpoint:
                return auth_method
        trusted_endpoints = [i.endpoint for i in provider_auth_methods]
        raise ValueError(
            f"No identity provider matches endpoint `{self.issuer.endpoint}` in "
            f"provider's trusted identity providers {trusted_endpoints}."
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
                    issuer = self.get_issuer_matching_project(
                        issuers=self.issuers, project_sla=project_conf.sla
                    )
                    auth_method = self.get_auth_method_matching_issuer(
                        provider_auth_methods=self.provider_conf.identity_providers,
                        issuer_endpoint=issuer.endpoint,
                    )
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
                except (ValueError, AssertionError) as e:
                    self.error = True
                    self.logger.error(e)
                    self.logger.error("Skipping project")

        with ThreadPoolExecutor() as executor:
            siblings = executor.map(lambda x: x.get_provider_siblings(), connections)
        siblings = list(siblings)
        siblings = list(filter(lambda x: x is not None, siblings))
        self.error = any([x.error for x in connections])

        # Merge regions, identity providers and projects retrieved from previous
        # parallel step.
        identity_providers, projects, regions = self.merge_data(siblings)

        # Send data to kafka
        self.send_kafka_messages(
            regions.values(), identity_providers=identity_providers.values()
        )

        return ProviderCreateExtended(
            name=self.provider_conf.name,
            type=self.provider_conf.type,
            is_public=self.provider_conf.is_public,
            support_emails=self.provider_conf.support_emails,
            status=self.provider_conf.status,
            identity_providers=identity_providers.values(),
            projects=projects.values(),
            regions=regions.values(),
        )

    def update_idp_user_groups(
        self,
        *,
        current_issuer: IdentityProviderCreateExtended,
        new_issuer: IdentityProviderCreateExtended,
    ) -> IdentityProviderCreateExtended:
        """
        Update the identity provider user groups.

        Since for each provider a user group can have just one SLA pointing to exactly
        one project. If the user group is not already in the current identity provider
        user groups add it, otherwise skip.
        """
        names = [i.name for i in current_issuer.user_groups]
        if new_issuer.user_groups[0].name not in names:
            current_issuer.user_groups.append(new_issuer.user_groups[0])
        return current_issuer

    def update_region_services(
        self, *, current_region: RegionCreateExtended, new_region: RegionCreateExtended
    ) -> RegionCreateExtended:
        """Update region services."""
        current_region.block_storage_services = (
            self.update_region_block_storage_services(
                current_services=current_region.block_storage_services,
                new_services=new_region.block_storage_services,
            )
        )
        current_region.compute_services = self.update_region_compute_services(
            current_services=current_region.compute_services,
            new_services=new_region.compute_services,
        )
        current_region.identity_services = self.update_region_identity_services(
            current_services=current_region.identity_services,
            new_services=new_region.identity_services,
        )
        current_region.network_services = self.update_region_network_services(
            current_services=current_region.network_services,
            new_services=new_region.network_services,
        )
        current_region.object_store_services = self.update_region_object_store_services(
            current_services=current_region.object_store_services,
            new_services=new_region.object_store_services,
        )
        return current_region

    def update_region_block_storage_services(
        self,
        *,
        current_services: list[BlockStorageServiceCreateExtended],
        new_services: list[BlockStorageServiceCreateExtended],
    ) -> list[BlockStorageServiceCreateExtended]:
        """Update Block Storage services.

        If the service does not exist, add it; otherwise, add new quotas.
        """
        for new_service in new_services:
            for service in current_services:
                if service.endpoint == new_service.endpoint:
                    service.quotas += new_service.quotas
                    break
            else:
                current_services.append(new_service)
        return current_services

    def update_region_compute_services(
        self,
        *,
        current_services: list[ComputeServiceCreateExtended],
        new_services: list[ComputeServiceCreateExtended],
    ) -> list[ComputeServiceCreateExtended]:
        """Update Compute services.

        If the service does not exist, add it; otherwise, add new quotas, flavors and
        images.
        """
        for new_service in new_services:
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
        return current_services

    def update_region_identity_services(
        self,
        *,
        current_services: list[IdentityServiceCreate],
        new_services: list[IdentityServiceCreate],
    ) -> list[IdentityServiceCreate]:
        """Update Identity services.

        If the service does not exist, add it.
        """
        for new_service in new_services:
            for service in current_services:
                if service.endpoint == new_service.endpoint:
                    break
            else:
                current_services.append(new_service)
        return current_services

    def update_region_network_services(
        self,
        *,
        current_services: list[NetworkServiceCreateExtended],
        new_services: list[NetworkServiceCreateExtended],
    ) -> list[NetworkServiceCreateExtended]:
        """Update Network services.

        If the service does not exist, add it; otherwise, add new quotas and networks.
        """
        for new_service in new_services:
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
        return current_services

    def update_region_object_store_services(
        self,
        *,
        current_services: list[ObjectStoreServiceCreateExtended],
        new_services: list[ObjectStoreServiceCreateExtended],
    ) -> list[ObjectStoreServiceCreateExtended]:
        """Update Object store services.

        If the service does not exist, add it; otherwise, add new quotas and networks.
        """
        for new_service in new_services:
            for service in current_services:
                if service.endpoint == new_service.endpoint:
                    service.quotas += new_service.quotas
                    break
            else:
                current_services.append(new_service)
        return current_services

    def filter_projects_on_compute_service(
        self, *, service: ComputeServiceCreateExtended, include_projects: list[str]
    ) -> tuple[list[FlavorCreateExtended], list[ImageCreateExtended]]:
        """Remove from compute resources projects not imported in the Fed-Reg.

        Apply the filtering only on private flavors and images.

        Since resources not matching at least the project used to discover them have
        already been discarded, on a specific resource, after the filtering projects,
        there can't be an empty projects list.
        """
        for flavor in filter(lambda x: not x.is_public, service.flavors):
            flavor.projects = list(
                filter(lambda x: x in include_projects, flavor.projects)
            )
        for image in filter(lambda x: not x.is_public, service.images):
            image.projects = list(
                filter(lambda x: x in include_projects, image.projects)
            )
        return service.flavors, service.images

    def merge_data(
        self, siblings: list[ProviderSiblings]
    ) -> tuple[
        list[IdentityProviderCreateExtended],
        list[ProjectCreate],
        list[RegionCreateExtended],
    ]:
        """Merge regions, identity providers and projects."""
        identity_providers: dict[str, IdentityProviderCreateExtended] = {}
        projects: dict[str, ProjectCreate] = {}
        regions: dict[str, RegionCreateExtended] = {}

        for sibling in siblings:
            projects[sibling.project.uuid] = sibling.project
            if identity_providers.get(sibling.identity_provider.endpoint) is None:
                identity_providers[
                    sibling.identity_provider.endpoint
                ] = sibling.identity_provider
            else:
                identity_providers[
                    sibling.identity_provider.endpoint
                ] = self.update_idp_user_groups(
                    current_issuer=identity_providers[
                        sibling.identity_provider.endpoint
                    ],
                    new_issuer=sibling.identity_provider,
                )
            if regions.get(sibling.region.name) is None:
                regions[sibling.region.name] = sibling.region
            else:
                regions[sibling.region.name] = self.update_region_services(
                    current_region=regions[sibling.region.name],
                    new_region=sibling.region,
                )

        # Filter non-federated projects from shared resources
        for region in regions.values():
            for service in region.compute_services:
                flavors, images = self.filter_projects_on_compute_service(
                    service=service, include_projects=projects.keys()
                )
                service.flavors = flavors
                service.images = images

        return identity_providers, projects, regions

    def send_kafka_messages(
        self,
        regions: list[RegionCreateExtended],
        identity_providers: list[IdentityProviderCreateExtended],
    ):
        """Organize quotas data and send them to kafka."""
        if self.kafka_prod is not None:
            for region in regions:
                data_list = {}
                for service in [
                    *region.block_storage_services,
                    *region.compute_services,
                    *region.network_services,
                ]:
                    service_type = service.type.replace("-", "_")
                    service_endpoint = str(service.endpoint)
                    for quota in service.quotas:
                        data_list[quota.project] = data_list.get(quota.project, {})
                        data_list[quota.project][service_endpoint] = data_list[
                            quota.project
                        ].get(
                            service_endpoint,
                            {f"{service_type}_service": service_endpoint},
                        )
                        for k, v in quota.dict(
                            exclude={
                                "description",
                                "per_user",
                                "project",
                                "type",
                                "usage",
                            }
                        ).items():
                            if quota.usage:
                                data_list[quota.project][service_endpoint][
                                    f"{service_type}_usage_{k}"
                                ] = v
                            else:
                                data_list[quota.project][service_endpoint][
                                    f"{service_type}_limit_{k}"
                                ] = v

                for project, value in data_list.items():
                    issuer, user_group = self.find_issuer_and_user_group(
                        identity_providers, project
                    )
                    msg_data = {
                        "provider": self.provider_conf.name,
                        "region": region.name,
                        "project": project,
                        "issuer": issuer,
                        "user_group": user_group,
                    }
                    for data in value.values():
                        msg_data = {**msg_data, **data}
                    self.kafka_prod.send(msg_data)

    def find_issuer_and_user_group(
        self, identity_providers: list[IdentityProviderCreateExtended], project: str
    ) -> tuple[str, str]:
        """Return issuer and user group matching project."""
        for issuer in identity_providers:
            for user_group in issuer.user_groups:
                if project == user_group.sla.project:
                    return str(issuer.endpoint), user_group.name
