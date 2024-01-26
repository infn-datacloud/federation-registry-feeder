from typing import List, Tuple

from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    RegionCreateExtended,
    SLACreateExtended,
    UserGroupCreateExtended,
)

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import PerRegionProps, Project, TrustedIDP


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
    *, issuers: List[Issuer], trusted_issuers: List[TrustedIDP], project: Project
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
                        auth_methods=trusted_issuers,
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
    auth_methods: List[TrustedIDP],
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
    *, project_conf: Project, region_props: PerRegionProps
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
