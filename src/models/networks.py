"""Pydantic models of the Virtual Machine Network owned by a Provider."""

import uuid
from typing import Annotated, Self

from pydantic import Field, model_validator

from src.models.core import BaseNode
from src.utils import find_duplicates


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
    projects: Annotated[
        list[uuid.UUID],
        Field(
            default_factory=list,
            description="List of projects' UUID allowed to use this network.",
        ),
    ]

    @model_validator(mode="after")
    def validate_projects_and_gpus(self) -> Self:
        """Verify consistency between gpus values and shared-projects values."""
        if self.is_shared:
            if len(self.projects) > 0:
                raise ValueError(
                    "A shared network does not have a list of proprietary projects"
                )
        else:
            if len(self.projects) == 0:
                raise ValueError(
                    "A private network must have at least a proprietary project"
                )
            find_duplicates(self.projects)
        return self
