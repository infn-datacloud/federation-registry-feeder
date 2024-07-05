from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

from fed_reg.provider.enum import ProviderStatus, ProviderType
from fed_reg.provider.schemas_extended import (
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

from src.logger import create_logger
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import AuthMethod, PerRegionProps, Project, Provider, Region
from src.providers.openstack import OpenstackData


def filter_projects_on_compute_service(
    *, service: ComputeServiceCreateExtended, include_projects: List[str]
) -> None:
    """Remove from compute resources projects not imported in the Federation-Registry.

    Apply the filtering only on public flavors and images.

    Since resources not matching at least the project used to discover them have already
    been discarded, on a specific resource, after the filtering projects, there can't be
    an empty projects list.
    """
    for flavor in filter(lambda x: not x.is_public, service.flavors):
        flavor.projects = list(filter(lambda x: x in include_projects, flavor.projects))
    for image in filter(lambda x: not x.is_public, service.images):
        image.projects = list(filter(lambda x: x in include_projects, image.projects))


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
    *, new_issuers: List[IdentityProviderCreateExtended]
) -> List[IdentityProviderCreateExtended]:
    d = {}
    for new_issuer in new_issuers:
        current_issuer: IdentityProviderCreateExtended = d.get(new_issuer.endpoint)
        if not current_issuer:
            d[new_issuer.endpoint] = new_issuer
        else:
            # Since for each provider a user group can have just one SLA pointing to
            # exactly one project. If the user group is not already in the current
            # identity provider user groups add it, otherwise skip.
            names = [i.name for i in current_issuer.user_groups]
            if new_issuer.user_groups[0].name not in names:
                current_issuer.user_groups.append(new_issuer.user_groups[0])
    return list(d.values())


def update_region_block_storage_services(
    *,
    current_services: List[BlockStorageServiceCreateExtended],
    new_services: List[BlockStorageServiceCreateExtended],
) -> None:
    for new_service in new_services:
        for service in current_services:
            if service.endpoint == new_service.endpoint:
                service.quotas += new_service.quotas
                break
        else:
            current_services.append(new_service)


def update_region_compute_services(
    *,
    current_services: List[ComputeServiceCreateExtended],
    new_services: List[ComputeServiceCreateExtended],
) -> None:
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


def update_region_identity_services(
    *,
    current_services: List[IdentityServiceCreate],
    new_services: List[IdentityServiceCreate],
) -> None:
    for new_service in new_services:
        for service in current_services:
            if service.endpoint == new_service.endpoint:
                break
        else:
            current_services.append(new_service)


def update_region_network_services(
    *,
    current_services: List[NetworkServiceCreateExtended],
    new_services: List[NetworkServiceCreateExtended],
) -> None:
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


def update_regions(
    *, new_regions: List[RegionCreateExtended], include_projects: List[str]
) -> List[RegionCreateExtended]:
    d = {}
    for new_region in new_regions:
        if len(new_region.compute_services) > 0:
            filter_projects_on_compute_service(
                service=new_region.compute_services[0],
                include_projects=include_projects,
            )
        current_region: RegionCreateExtended = d.get(new_region.name)
        if not current_region:
            d[new_region.name] = new_region
        else:
            update_region_block_storage_services(
                current_services=current_region.block_storage_services,
                new_services=new_region.block_storage_services,
            )
            update_region_compute_services(
                current_services=current_region.compute_services,
                new_services=new_region.compute_services,
            )
            update_region_identity_services(
                current_services=current_region.identity_services,
                new_services=new_region.identity_services,
            )
            update_region_network_services(
                current_services=current_region.network_services,
                new_services=new_region.network_services,
            )
    return list(d.values())


class ConnectionThread:
    def __init__(
        self,
        *,
        provider_conf: Provider,
        region_conf: Region,
        project_conf: Project,
        issuers: List[Issuer],
        log_level: str,
    ) -> None:
        self.provider_conf = provider_conf
        self.region_conf = region_conf
        self.project_conf = project_conf
        self.issuers = issuers
        self.log_level = log_level
        logger_name = f"Provider {self.provider_conf.name}, "
        logger_name += f"Region {self.region_conf.name}, "
        logger_name += f"Project {self.project_conf.id}"
        self.logger = create_logger(logger_name, level=log_level)

    def get_idp_project_and_region(
        self,
    ) -> Optional[
        Tuple[IdentityProviderCreateExtended, ProjectCreate, RegionCreateExtended]
    ]:
        # Find region props matching current region.
        region_props = next(
            filter(
                lambda x: x.region_name == self.region_conf.name,
                self.project_conf.per_region_props,
            ),
            None,
        )
        proj_conf = get_project_conf_params(
            project_conf=self.project_conf, region_props=region_props
        )

        try:
            identity_provider, token = get_identity_provider_info_for_project(
                issuers=self.issuers,
                auth_methods=self.provider_conf.identity_providers,
                project=proj_conf,
            )
        except ValueError as e:
            self.logger.error(e)
            self.logger.error("Skipping project")
            return None

        if self.provider_conf.type == ProviderType.OS.value:
            data = OpenstackData(
                provider_conf=self.provider_conf,
                project_conf=proj_conf,
                region_name=self.region_conf.name,
                identity_provider=identity_provider,
                token=token,
                logger=self.logger,
            )
        if self.provider_conf.type == ProviderType.K8S.value:
            # Not yet implemented
            data = None
        if not data:
            return None

        region = RegionCreateExtended(
            **self.region_conf.dict(),
            block_storage_services=[data.block_storage_service]
            if data.block_storage_service
            else [],
            compute_services=[data.compute_service] if data.compute_service else [],
            identity_services=[data.identity_service] if data.identity_service else [],
            network_services=[data.network_service] if data.network_service else [],
        )

        return identity_provider, data.project, region


class ProviderThread:
    def __init__(
        self, *, provider_conf: Provider, issuers: List[Issuer], log_level: str
    ) -> None:
        self.provider_conf = provider_conf
        self.issuers = issuers
        self.log_level = log_level
        self.logger = create_logger(
            f"Provider {self.provider_conf.name}", level=log_level
        )

    def get_provider(self) -> ProviderCreateExtended:
        """Generate an Openstack virtual provider, reading information from a real
        openstack instance.
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

        inputs: list[ConnectionThread] = []
        for region_conf in self.provider_conf.regions:
            for project_conf in self.provider_conf.projects:
                inputs.append(
                    ConnectionThread(
                        provider_conf=self.provider_conf,
                        region_conf=region_conf,
                        project_conf=project_conf,
                        issuers=self.issuers,
                        log_level=self.log_level,
                    )
                )

        with ThreadPoolExecutor() as executor:
            responses = executor.map(lambda x: x.get_idp_project_and_region(), inputs)
        responses = list(filter(lambda x: x, responses))

        identity_providers = []
        projects = []
        regions = []
        if len(responses) > 0:
            (identity_providers, projects, regions) = zip(*responses)

            projects = list({i.uuid: i for i in projects}.values())
            identity_providers = update_identity_providers(
                new_issuers=identity_providers
            )
            regions = update_regions(
                new_regions=regions, include_projects=[i.uuid for i in projects]
            )

        return ProviderCreateExtended(
            name=self.provider_conf.name,
            type=self.provider_conf.type,
            is_public=self.provider_conf.is_public,
            support_emails=self.provider_conf.support_emails,
            status=self.provider_conf.status,
            identity_providers=identity_providers,
            projects=projects,
            regions=regions,
        )
