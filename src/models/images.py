"""Pydantic models of the Virtual Machine Image owned by a Provider."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Self

from pydantic import Field, model_validator

from src.models.core import BaseNode
from src.utils import find_duplicates


class ImageOS(str, Enum):
    """Possible operating systems types."""

    Linux: str = "Linux"
    Windows: str = "Windows"
    MacOS: str = "MacOS"

    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        return None


class Image(BaseNode):
    """Model with Image public and restricted attributes.

    Attributes:
    ----------
        description (str): Brief description.
        name (str): Image name in the Provider.
        uuid (str): Image unique ID in the Provider
        os_type (str | None): OS type.
        os_distro (str | None): OS distribution.
        os_version (str | None): Distribution version.
        architecture (str | None): OS architecture.
        kernel_id (str | None): Kernel version.
        cuda_support (str): Support for cuda enabled.
        gpu_driver (str): Support for GPUs drivers enabled.
        created_at (datetime | None): Creation time.
        tags (list of str): list of tags associated to this Image.
    """

    name: Annotated[str, Field(description="Image name in the Resource Provider.")]
    iaas_uuid: Annotated[
        str, Field(description="Image unique ID in the Resource Provider.")
    ]
    os_type: Annotated[ImageOS | None, Field(default=None, description="OS type.")]
    os_distro: Annotated[
        str | None, Field(default=None, description="OS distribution.")
    ]
    os_version: Annotated[
        str | None, Field(default=None, description="Distribution version.")
    ]
    architecture: Annotated[
        str | None, Field(default=None, description="OS architecture.")
    ]
    kernel_id: Annotated[str | None, Field(default=None, description="Kernel version.")]
    cuda_support: Annotated[
        bool, Field(default=False, description="Support for cuda enabled.")
    ]
    gpu_driver: Annotated[
        bool, Field(default=False, description="Support for GPUs drivers enabled.")
    ]
    created_at: Annotated[
        datetime | None, Field(default=None, description="Creation time")
    ]
    tags: Annotated[
        list[str],
        Field(
            default_factory=list, description="List of tags associated to this Image."
        ),
    ]
    is_shared: Annotated[bool, Field(description="Public or private Image.")]
    projects: Annotated[
        list[uuid.UUID],
        Field(
            default_factory=list,
            description="List of projects' UUID allowed to use this image.",
        ),
    ]

    @model_validator(mode="after")
    def validate_projects_and_gpus(self) -> Self:
        """Verify consistency between gpus values and shared-projects values."""
        if self.is_shared:
            if len(self.projects) > 0:
                raise ValueError(
                    "A shared image does not have a list of proprietary projects"
                )
        else:
            if len(self.projects) == 0:
                raise ValueError(
                    "A private image must have at least a proprietary project"
                )
            find_duplicates(self.projects)
        return self
