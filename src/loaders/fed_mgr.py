"""Functions to read from Fed-Mgr the configurations of the federated providers."""

import urllib.parse
import uuid
from typing import Any

import requests
from fed_mgr.v1 import IDPS_PREFIX, PROVIDERS_PREFIX
from fed_mgr.v1.identity_providers.schemas import IdentityProviderRead
from fed_mgr.v1.identity_providers.user_groups.schemas import UserGroupRead
from fed_mgr.v1.identity_providers.user_groups.slas.schemas import SLARead
from fed_mgr.v1.providers.identity_providers.schemas import ProviderIdPConnectionRead
from fed_mgr.v1.providers.projects.regions.schemas import ProjRegConnectionRead
from fed_mgr.v1.providers.projects.schemas import ProjectRead
from fed_mgr.v1.providers.regions.schemas import RegionRead
from fed_mgr.v1.providers.schemas import ProviderRead
from pydantic import AnyHttpUrl

from src.loaders.utils import complete_partial_connection, create_partial_connection
from src.models.site_config import SiteConfig


def get_idps(base_url: AnyHttpUrl) -> list[IdentityProviderRead]:
    """Retreive the list of trusted identity providers from fed-mgr.

    Args:
        base_url (AnyHttpUrl): Fed-mgr base url.

    Returns:
        list of IdentityProviderRead: list of identity providers.

    """
    url = urllib.parse.urljoin(str(base_url), IDPS_PREFIX[1:])
    resp = requests.get(url)
    if resp.ok:
        return [IdentityProviderRead(i) for i in resp.json()["data"]]


def get_providers(base_url: AnyHttpUrl) -> list[ProviderRead]:
    """Retreive the list of providers from fed-mgr.

    Args:
        base_url (AnyHttpUrl): Fed-mgr base url.

    Returns:
        list of ProviderRead: list of providers.

    """
    url = urllib.parse.urljoin(str(base_url), PROVIDERS_PREFIX[1:])
    resp = requests.get(url, params={"status": "active"})
    if resp.ok:
        return [ProviderRead(i) for i in resp.json()["data"]]


def get_provider_idps(provider: ProviderRead) -> list[ProviderIdPConnectionRead]:
    """Retreive the list of identity providers trusted by a provider from fed-mgr.

    Args:
        provider (ProviderRead): parent resource provider.

    Returns:
        list of ProviderIdPConnectionRead: list of identity providers with overrides.

    """
    resp = requests.get(str(provider.links.idps))
    if resp.ok:
        return [ProviderIdPConnectionRead(i) for i in resp.json()["data"]]


def get_provider_regions(provider: ProviderRead) -> list[RegionRead]:
    """Retreive the list of regions hosted by a provider from fed-mgr.

    Args:
        provider (ProviderRead): parent resource provider.

    Returns:
        list of RegionRead: list of regions.

    """
    resp = requests.get(str(provider.links.regions))
    if resp.ok:
        return [RegionRead(i) for i in resp.json()["data"]]


def get_provider_projects(provider: ProviderRead) -> list[ProjectRead]:
    """Retreive the list of projects hosted by a provider from fed-mgr.

    Args:
        provider (ProviderRead): parent resource provider.

    Returns:
        list of ProjectRead: list of projects.

    """
    resp = requests.get(provider.links.projects)
    if resp.ok:
        return [ProjectRead(i) for i in resp.json()["data"]]


def get_idp_groups(idp: IdentityProviderRead) -> list[UserGroupRead]:
    """Retreive the list of user groups owned by an identity provider from fed-mgr.

    Args:
        idp (IdentityProviderRead): parent identity provider.

    Returns:
        list of UserGroupRead: list of user groups.

    """
    resp = requests.get(str(idp.links.user_groups))
    if resp.ok:
        return [UserGroupRead(i) for i in resp.json()["data"]]


def get_group_slas(group: UserGroupRead) -> list[SLARead]:
    """Retreive the list of SLA signed by a user group from fed-mgr.

    Args:
        group (UserGroupRead): parent user group.

    Returns:
        list of SLARead: list of SLA.

    """
    resp = requests.get(str(group.links.slas))
    if resp.ok:
        return [SLARead(i) for i in resp.json()["data"]]


def get_sla_projects(sla: SLARead) -> list[ProjectRead]:
    """Retreive the list of projects involved in a SLA from fed-mgr.

    Args:
        sla (SLARead): parent SLA.

    Returns:
        list of ProjectRead: list of projects.

    """
    resp = requests.get(str(sla.links.projects), params={"sla_id": sla.id})
    if resp.ok:
        return [ProjectRead(i) for i in resp.json()["data"]]


def get_project_configs(project: ProjectRead) -> list[ProjRegConnectionRead]:
    """Retreive the list of identity providers trusted by a provider from fed-mgr.

    Args:
        project (ProjectRead): parent resource provider.

    Returns:
        list of ProviderIdPConnectionRead: list of identity providers with overrides.

    """
    resp = requests.get(str(project.links.regions))
    if resp.ok:
        return [ProjRegConnectionRead(i) for i in resp.json()["data"]]


def merge_idp_with_overrides(
    idps: list[IdentityProviderRead], idp_overrides: list[ProviderIdPConnectionRead]
) -> list[IdentityProviderRead]:
    """Merge the default idp attributes with the corresponding overrides.

    Args:
        idps (list of IdentityProviderRead): list of the identity providers registered
            in the fed-mgr.
        idp_overrides (list of ProviderIdPConnectionRead): list of the overrides to
            apply to a subset of idps.

    Returns:
        list of IdentityProviderRead: filtered list of identity providers with applied
            overrides.

    """
    new_idps = []
    for idp_over in idp_overrides:
        for idp in idps:
            if idp_over.idp_id == idp.id:
                data = idp.model_dump()
                if idp_over.overrides.groups_claim is None:
                    data["groups_claim"] = idp.groups_claim
                else:
                    data["groups_claim"] = idp_over.overrides.groups_claim
                if idp_over.overrides.protocol is None:
                    data["protocol"] = idp.protocol
                else:
                    data["protocol"] = idp_over.overrides.protocol
                if idp_over.overrides.name is None:
                    data["name"] = idp.name
                else:
                    data["name"] = idp_over.overrides.name
                if idp_over.overrides.audience is None:
                    data["audience"] = idp.audience
                else:
                    data["audience"] = idp_over.overrides.audience
                new_idps.append(IdentityProviderRead(**data))
                break
    return new_idps


def complete_partial_connections(
    partial_connections: dict[uuid.UUID, dict[str, Any]],
    idps: list[IdentityProviderRead],
) -> list[SiteConfig]:
    """Read partial connections and retrieve details from trusted idps.

    For each project of an sla of a user group of an idp, retrieve the correspondin
    partial connection (if present) and populate the idp info. Add each new connection
    to the input list.

    Args:
        idps (list of IdentityProvider): list of trusted identity providers.
        connections (list of SiteConfig): list of connections to be expanded.
        partial_connections (dict of {str: dict}): partial connections. The key is the
            project's ID and the value is another dict. These one has the idp endpoint
            as key and the idp data as value

    Returns:
        list of Connections:

    """
    connections = []
    for idp in idps:
        groups = get_idp_groups(idp)
        for group in groups:
            slas = get_group_slas(group)
            for sla in slas:
                projects = get_sla_projects(sla)
                for project in projects:
                    conn_params = partial_connections.pop(project.id, None)
                    if conn_params is not None:
                        conn_params["user_group"] = group.name
                        conn = complete_partial_connection(conn_params, idp.endpoint)
                        connections.append(conn)
    return connections


def list_conn_params_from_providers(
    providers: list[ProviderRead], trusted_idps: list[IdentityProviderRead]
) -> list[SiteConfig]:
    """From the list of providers retrieve the list of connection parameters.

    Args:
        providers (list of Provider): list of provider's configuration
        trusted_idps (list of IdentityProviderRead): list of trusted identity providers

    Returns:
        (list of SiteConfig, dict): tuple with the list of connections and a dict with
            the project id and the partial connection parameters.

    """
    partial_connections = {}

    for provider in providers:
        idp_overrides = get_provider_idps(provider)
        regions = get_provider_regions(provider)
        projects = get_provider_projects(provider)
        idps = merge_idp_with_overrides(trusted_idps, idp_overrides)
        ca_path = None
        # TODO load CA from S3 and create file?
        for project in projects:
            configs = get_project_configs(project)
            for region in regions:
                kwargs = {
                    "provider_name": provider.name,
                    "provider_type": provider.type,
                    "provider_endpoint": provider.auth_endpoint,
                    "image_tags": provider.image_tags,
                    "network_tags": provider.network_tags,
                    "region_name": region.name,
                    "overbooking_cpu": region.overbooking_cpu,
                    "overbooking_ram": region.overbooking_ram,
                    "bandwidth_in": region.bandwidth_in,
                    "bandwidth_out": region.bandwidth_out,
                    "project_id": project.id,
                    "ca_path": ca_path,
                }
                for config in configs:
                    if region.id in config.region_id:
                        kwargs = {
                            **kwargs,
                            **config.overrides.model_dump(exclude_unset=True),
                        }
                # The provider support multiple idps. An intersection between the
                # project and the authorized user group is needed
                data = create_partial_connection(idps=idps, **kwargs)
                partial_connections[project.id] = data

    connections = complete_partial_connections(partial_connections, trusted_idps)

    return connections


def load_connections_from_fed_mgr(base_url: AnyHttpUrl) -> list[SiteConfig]:
    """Retrieve the list of connections from fed-mgr.

    Read the folder content and parse the yaml files content.

    Args:
        base_url (AnyHttpUrl): Federation-Manager URl.

    Returns:
        list(Connections): list of connection parameters

    """
    trusted_idps = get_idps(base_url)
    providers = get_providers(base_url)
    connections = list_conn_params_from_providers(providers, trusted_idps)
    return connections
