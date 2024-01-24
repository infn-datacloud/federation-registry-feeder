from typing import List

from src.models.identity_provider import Issuer
from src.models.provider import PerRegionProps, Project, TrustedIDP


def get_identity_provider_for_project(
    *, issuers: List[Issuer], trusted_idps: List[TrustedIDP], project: Project
) -> Issuer:
    """Find the identity provider with an SLA matching the one of target project.

    For each sla of each user group of each issuer listed in the yaml file, find the one
    matching the SLA of the target project. Add project id to SLA's project list if not
    present.
    """
    for issuer in issuers:
        for user_group in issuer.user_groups:
            for sla in user_group.slas:
                if sla.doc_uuid == project.sla:
                    # Found matching SLA.
                    if project.id not in sla.projects:
                        sla.projects.append(project.id)
                    return update_issuer_auth_method(
                        issuer=issuer, auth_methods=trusted_idps
                    )
    raise ValueError(
        f"No SLA matching doc_uuid `{project.sla}` in project configuration"
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


def update_issuer_auth_method(*, issuer: Issuer, auth_methods: List[TrustedIDP]):
    for auth_method in auth_methods:
        if auth_method.endpoint == issuer.endpoint:
            issuer.relationship = auth_method
            return issuer
    raise ValueError(
        f"No identity provider matching endpoint `{issuer.endpoint}` in provider "
        f"trusted identity providers {[i.endpoint for i in auth_methods]}"
    )
