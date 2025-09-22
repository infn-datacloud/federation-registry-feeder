"""Pydantic models of the Virtual Machine Flavor owned by a Provider."""

import uuid
from typing import Annotated, Self

from pydantic import Field, model_validator

from src.models.core import BaseNode
from src.utils import find_duplicates


class Flavor(BaseNode):
    """Model with Flavor public and restricted attributes.

    Attributes:
    ----------
        description (str): Brief description.
        name (str): Flavor name in the Resource Provider.
        uuid (str): Flavor unique ID in the Resource Provider.
        disk (int): Reserved disk size (GiB).
        ram (int): Reserved RAM (MiB).
        vcpus (int): Number of Virtual CPUs.
        swap (int): Swap size (GiB).
        ephemeral (int): Ephemeral disk size (GiB).
        infiniband (bool): MPI - parallel multi-process enabled.
        gpus (int): Number of GPUs.
        gpu_model (str | None): GPU model name.
        gpu_vendor (str | None): Name of the GPU vendor.
        local_storage (str | None): Local storage presence.
    """

    iaas_uuid: Annotated[
        str, Field(description="Flavor unique ID in the Resource Provider.")
    ]
    name: Annotated[str, Field(description="Flavor name in the Resource Provider.")]
    disk: Annotated[
        int, Field(default=0, ge=0, description="Reserved disk size (GiB).")
    ]
    ram: Annotated[int, Field(default=0, ge=0, description="Reserved RAM (MiB).")]
    vcpus: Annotated[int, Field(default=0, ge=0, description="Number of Virtual CPUs.")]
    swap: Annotated[int, Field(default=0, ge=0, description="Swap size (GiB).")]
    ephemeral: Annotated[
        int, Field(default=0, ge=0, description="Ephemeral disk size (GiB).")
    ]
    infiniband: Annotated[
        bool, Field(default=False, description="MPI - parallel multi-process enabled.")
    ]
    gpu_model: Annotated[str | None, Field(default=None, description="GPU model name.")]
    gpu_vendor: Annotated[
        str | None, Field(default=None, description="Name of the GPU vendor.")
    ]
    gpus: Annotated[int, Field(default=0, ge=0, description="Number of GPUs.")]
    local_storage: Annotated[
        str | None, Field(default=None, description="Local storage presence.")
    ]
    is_shared: Annotated[bool, Field(description="Public or private Flavor.")]
    projects: Annotated[
        list[uuid.UUID],
        Field(
            default_factory=list,
            description="List of projects' UUID allowed to use this flavor.",
        ),
    ]

    @model_validator(mode="after")
    def validate_projects_and_gpus(self) -> Self:
        """Verify consistency between gpus values and shared-projects values."""
        if self.gpus == 0:
            if self.gpu_model is not None:
                raise ValueError("'GPU model' must be None if 'Num GPUs' is 0")
            if self.gpu_vendor is not None:
                raise ValueError("'GPU vendor' must be None if 'Num GPUs' is 0")

        if self.is_shared:
            if len(self.projects) > 0:
                raise ValueError(
                    "A shared flavor does not have a list of proprietary projects"
                )
        else:
            if len(self.projects) == 0:
                raise ValueError(
                    "A private flavor must have at least a proprietary project"
                )
            find_duplicates(self.projects)

        return self
