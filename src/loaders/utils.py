"""Loaders utilities."""

from typing import Any

from fed_mgr.v1.identity_providers.schemas import IdentityProviderBase
from fed_mgr.v1.providers.schemas import ProviderType
from pydantic import AnyHttpUrl

from src.models.site_config import SiteConfig


def create_partial_connection(
    *, idps: list[IdentityProviderBase], **kwargs
) -> dict[str, Any]:
    """Create a dictionary with the connection parameters.

    Args:
        idps (list of IdentityProviderBase): vailable identity providers
        kwargs: attributes to build the connection

    Returns:
        dict of {str, Any}: object with the connection parameters and the idps.

    """
    conn_params = {**kwargs}
    conn_params["idps"] = {idp.endpoint: idp for idp in idps}
    return conn_params


def complete_partial_connection(
    conn_params: dict[str, Any], idp_endpoint: AnyHttpUrl
) -> SiteConfig:
    """From a dict with connection params create a connection matching the target idp.

    Args:
        conn_params (dics of {str, Any}): dict with the connection params.
        idp_endpoint (AnyHttpUrl): target idp's endpoint.

    Returns:
        SiteConfig: object with the connection parameters.

    """
    conn_idps = conn_params.pop("idps", {})
    conn_idp: IdentityProviderBase | None = conn_idps.get(idp_endpoint, None)
    if conn_idp is not None:
        conn_params["idp_endpoint"] = conn_idp.endpoint
        if conn_params["provider_type"] == ProviderType.openstack:
            conn_params["idp_protocol"] = conn_idp.protocol
            conn_params["idp_name"] = conn_idp.name
        elif conn_params["provider_type"] == ProviderType.kubernetes:
            conn_params["idp_audience"] = conn_idp.audience
        return SiteConfig(**conn_params)
