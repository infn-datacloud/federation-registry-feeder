"""Models for Kubernetes storageclass entity."""

from typing import Annotated

from pydantic import Field

from src.models.core import BaseNode


class StorageClass(BaseNode):
    """Model with StorageClass public and restricted attributes."""

    name: Annotated[str, Field(description="StorageClass name")]
    is_default: Annotated[
        bool,
        Field(default=False, description="StorageClass is the cluster default one"),
    ]
    provisioner: Annotated[
        str,
        Field(
            description="A provisioner determines what volume plugin is used for "
            "provisioning PVs"
        ),
    ]
