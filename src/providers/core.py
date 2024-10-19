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
    SLACreateExtended,
    UserGroupCreateExtended,
)

from src.kafka_conn import Producer
from src.logger import create_logger
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import Project, Provider, ProviderSiblings
from src.providers.openstack import OpenstackData, ProviderException


class ConnectionThread:
    """Data shared between the same connection socket"""

    def __init__(
        self,
        *,
        provider_conf: Provider,
        issuers: list[Issuer],
        log_level: str | int | None = None,
    ) -> None:
        assert (
            len(provider_conf.regions) == 1
        ), f"Invalid number or regions: {len(provider_conf.regions)}"
        assert (
            len(provider_conf.projects) == 1
        ), f"Invalid number or projects: {len(provider_conf.projects)}"

        self.provider_conf = provider_conf
        self.region_name = provider_conf.regions[0].name
        self.issuers = issuers

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
        project = self.get_project_conf_params()

        try:
            identity_provider, token = self.get_idp_matching_project(project)
        except ValueError as e:
            self.logger.error(e)
            self.logger.error("Skipping project")
            self.error = True
            return None

        if self.provider_conf.type == ProviderType.OS.value:
            try:
                data = OpenstackData(
                    provider_conf=self.provider_conf,
                    project_conf=project,
                    region_name=self.region_name,
                    identity_provider=identity_provider,
                    token=token,
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

    def get_project_conf_params(self) -> Project:
        """Get project parameters defined in the yaml file.

        If the `per_region_props` attribute has been defined and the current region name
        matches the name of the region definining the new props, override project's
        corresponding values.
        """
        # Find region props matching current region.
        region_props = filter(
            lambda x: x.region_name == self.region_name,
            self.provider_conf.projects[0].per_region_props,
        )
        region_props = next(region_props, None)

        new_conf = Project(
            **self.provider_conf.projects[0].dict(exclude={"per_region_props"})
        )
        if region_props:
            new_conf.default_private_net = region_props.default_private_net
            new_conf.default_public_net = region_props.default_public_net
            new_conf.private_net_proxy = region_props.private_net_proxy
            new_conf.per_user_limits = region_props.per_user_limits
        return new_conf

    def get_idp_matching_project(
        self, project: Project
    ) -> tuple[IdentityProviderCreateExtended, str]:
        """Find the identity provider with an SLA matching the target project's one.

        For each sla of each user group of each issuer listed in the yaml file, find the
        one matching the SLA of the target project.

        Return the indentity provider data and the token to use to establish the
        connection.
        """
        for issuer in self.issuers:
            for user_group in issuer.user_groups:
                for sla in user_group.slas:
                    if sla.doc_uuid == project.sla:
                        return self.get_identity_provider_with_auth_method(
                            issuer=issuer,
                            user_group=user_group,
                            sla=sla,
                            project=project.id,
                        ), issuer.token
        raise ValueError(
            f"No SLA matches doc_uuid `{project.sla}` in project configuration"
        )

    def get_identity_provider_with_auth_method(
        self, *, issuer: Issuer, user_group: UserGroup, sla: SLA, project: str
    ) -> IdentityProviderCreateExtended:
        """Generate the IdentityProvider instance."""
        for auth_method in self.provider_conf.identity_providers:
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
        trusted_endpoints = [i.endpoint for i in self.provider_conf.identity_providers]
        raise ValueError(
            f"No identity provider matches endpoint `{issuer.endpoint}` in provider "
            f"trusted identity providers {trusted_endpoints}."
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
        for region_conf in self.provider_conf.regions:
            for project_conf in self.provider_conf.projects:
                provider_conf = copy.deepcopy(self.provider_conf)
                provider_conf.regions = [region_conf]
                provider_conf.projects = [project_conf]
                connections.append(
                    ConnectionThread(
                        provider_conf=provider_conf,
                        issuers=self.issuers,
                        log_level=self.log_level,
                    )
                )

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
