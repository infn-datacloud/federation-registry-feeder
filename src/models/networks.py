"""Pydantic models of the Virtual Machine Network owned by a Provider."""

from typing import Annotated

from pydantic import Field

from src.models.core import BaseNode


class Network(BaseNode):
    """Model with Network public and restricted attributes.

    Attributes:
    ----------
        description (str): Brief description.
        name (str): Network name in the Provider.
        uuid (str): Network unique ID in the Provider
        is_router_external (bool): Network with access to outside networks. External
            network.
        is_default (bool): Network to use as default.
        mtu (int | None): Metric transmission unit (B).
        proxy_host (str | None): Proxy IP address.
        proxy_user (str | None): Proxy username.
        tags (list of str): list of tags associated to this Network.
    """

    name: Annotated[str, Field(description="Network name in the Resource Provider.")]
    iaas_uuid: Annotated[
        str, Field(description="Network unique ID in the Resource Provider.")
    ]
    is_router_external: Annotated[
        bool,
        Field(
            default=False,
            description="Network with access to outside networks. "
            "External/public network.",
        ),
    ]
    is_default: Annotated[bool, Field(description="Network to use as default.")]
    mtu: Annotated[
        int | None,
        Field(default=None, gt=0, description="Metric transmission unit (B)."),
    ]
    proxy_host: Annotated[
        str | None,
        Field(
            default=None,
            description="Proxy IP address or hostname. Accept port number.",
        ),
    ]
    proxy_user: Annotated[
        str | None, Field(default=None, description="Proxy username.")
    ]
    tags: Annotated[
        list[str],
        Field(
            default_factory=list, description="List of tags associated to this Network."
        ),
    ]
    is_shared: Annotated[bool, Field(description="Public or private network.")]
