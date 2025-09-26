"""Pydantic models of the Resource limitations for Projects on Services."""

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from src.models.core import BaseNode


class QuotaType(str, Enum):
    """Possible Quota types."""

    BLOCK_STORAGE = "block-storage"
    COMPUTE = "compute"
    NETWORK = "networking"
    OBJECT_STORE = "object-store"
    STORAGECLASS = "storageclass"


class QuotaBase(BaseNode):
    """Model with Quota common attributes.

    This model is used also as a public interface.

    Attributes:
    ----------
        description (str): Brief description.
        per_user (str): This limitation should be applied to each user.
        usage (str): This quota defines the current resource usage.
    """

    per_user: Annotated[
        bool,
        Field(
            default=False, description="This limitation should be applied to each user."
        ),
    ]
    usage: Annotated[
        bool,
        Field(
            default=False,
            description="Flag to determine if this quota represents the current usage.",
        ),
    ]


class BlockStorageQuota(QuotaBase):
    """Model with the Block Storage Quota public and restricted attributes.

    Model derived from QuotaBase to inherit attributes common to all quotas.

    Attributes:
    ----------
        description (str): Brief description.
        type (str): Quota type.
        per_user (str): This limitation should be applied to each user.
        usage (str): This quota defines the current resource usage.
        gigabytes (int | None): Number of max usable gigabytes (GiB).
        per_volume_gigabytes (int | None): Number of max usable gigabytes per volume
            (GiB).
        volumes (int | None): Number of max volumes a user group can create.
    """

    type: Annotated[
        Literal[QuotaType.BLOCK_STORAGE],
        Field(default=QuotaType.BLOCK_STORAGE, description="Block storage type"),
    ]
    gigabytes: Annotated[
        int | None,
        Field(default=None, ge=-1, description="Number of max usable gigabytes (GiB)."),
    ]
    per_volume_gigabytes: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="Number of max usable gigabytes per volume (GiB).",
        ),
    ]
    volumes: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="Number of max volumes a user group can create.",
        ),
    ]
    pvcs: Annotated[
        int | None,
        Field(
            default=None, ge=0, description="Total number of PVCs that can be created."
        ),
    ]
    storage: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Resources can define the minimum required storage. This is "
            "the maximum of the sum of all the resources' storage requests.",
        ),
    ]
    requests_ephemeral_storage: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Resources can define the minimum required ephemeral storage. "
            "This is the maximum of the sum of all the resources' ephemeral storage "
            "requests.",
        ),
    ]
    limits_ephemeral_storage: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Resources can define the maximum allowed ephemeral storage. "
            "This is the maximum of the sum of all the resources' ephemeral storage "
            "limits.",
        ),
    ]


class StorageClassQuota(QuotaBase):
    """Model with the Block Storage Quota public and restricted attributes.

    Model derived from QuotaBase to inherit attributes common to all quotas.

    Attributes:
    ----------
        description (str): Brief description.
        type (str): Quota type.
        per_user (str): This limitation should be applied to each user.
        usage (str): This quota defines the current resource usage.
        gigabytes (int | None): Number of max usable gigabytes (GiB).
        per_volume_gigabytes (int | None): Number of max usable gigabytes per volume
            (GiB).
        volumes (int | None): Number of max volumes a user group can create.
    """

    type: Annotated[
        Literal[QuotaType.STORAGECLASS],
        Field(default=QuotaType.STORAGECLASS, description="Storageclass type"),
    ]
    pvcs: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Total number of PVCs that can be created for this kind of "
            "storageclass.",
        ),
    ]
    storage: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Resources can define the minimum required storage. This is "
            "the maximum of the sum of all the resources' storage requests.",
        ),
    ]


class ComputeQuota(QuotaBase):
    """Model with the Compute Quota public and restricted attributes.

    Model derived from QuotaBase to inherit attributes common to all quotas.

    Attributes:
    ----------
        description (str): Brief description.
        type (str): Quota type.
        per_user (str): This limitation should be applied to each user.
        usage (str): This quota defines the current resource usage.
        cores (int | None): Number of max usable cores.
        instances (int | None): Number of max VM instances.
        ram (int | None): Number of max usable RAM (MiB).
        limits_cpu (int | None): Max value for the sum of the maximum usable cpus
            for a pod.
        requests_cpu (int | None): Max value for the sum of the "minimum required" cpus
            for a pod.
        limits_memory (int | None): Max value for the sum of the maximum usable memory
            for a pod.
        requests_memory (int | None): Max value for the sum of the "minimum required"
            memory for a pod.
        pods (int | None): Max number of pods that can be created.
        gpus (dict[str, int] | None): For each type of GPU, define the maximum quota.
    """

    type: Annotated[
        Literal[QuotaType.COMPUTE],
        Field(default=QuotaType.COMPUTE, description="Compute type"),
    ]
    cores: Annotated[
        int | None, Field(default=None, ge=0, description="Number of max usable cores.")
    ]
    instances: Annotated[
        int | None, Field(default=None, ge=0, description="Number of max VM instances.")
    ]
    ram: Annotated[
        int | None, Field(default=None, ge=0, description="Number of max VM instances.")
    ]
    limits_cpu: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Max value for the sum of the maximum usable cpus for a pod.",
        ),
    ]
    requests_cpu: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Max value for the sum of the minimum required cpus for a pod.",
        ),
    ]
    limits_memory: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Max value for the sum of the maximum usable memory for a pod.",
        ),
    ]
    requests_memory: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Max value for the sum of the min required memory for a pod.",
        ),
    ]
    pods: Annotated[
        int | None,
        Field(
            default=None, ge=0, description="Max number of pods that can be created."
        ),
    ]
    gpus: Annotated[
        dict[str, int] | None,
        Field(
            default=None, description="For each type of GPU, define the maximum quota."
        ),
    ]


class NetworkQuota(QuotaBase):
    """Model with the Network Quota public and restricted attributes.

    Model derived from QuotaBase to inherit attributes common to all quotas.

    Attributes:
    ----------
        description (str): Brief description.
        type (str): Quota type.
        per_user (str): This limitation should be applied to each user.
        usage (str): This quota defines the current resource usage.
        public_ips (int | None): The number of floating IP addresses allowed for each
            project.
        networks (int | None): The number of networks allowed for each project.
        ports (int | None): The number of ports allowed for each project.
        security_groups (int | None): The number of security groups allowed for each
            project.
        security_group_rules (int | None): The number of security group rules allowed
            for each project.
    """

    type: Annotated[
        Literal[QuotaType.NETWORK],
        Field(default=QuotaType.NETWORK, description="Network type"),
    ]
    public_ips: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of floating IP addresses allowed for each project.",
        ),
    ]
    networks: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of networks allowed for each project.",
        ),
    ]
    ports: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of ports allowed for each project.",
        ),
    ]
    security_groups: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of security groups allowed for each project.",
        ),
    ]
    security_group_rules: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of security group rules allowed for each project.",
        ),
    ]


class ObjectStoreQuota(QuotaBase):
    """Model with the Object Storage Quota public and restricted attributes.

    Model derived from QuotaBase to inherit attributes common to all quotas.

    Attributes:
    ----------
        description (str): Brief description.
        type (str): Quota type.
        per_user (str): This limitation should be applied to each user.
        usage (str): This quota defines the current resource usage.
        bytes (int): Maximum number of allowed bytes.
        containers (int): Maximum number of allowed containers.
        objects (int): Maximum number of allowed objects.
    """

    type: Annotated[
        Literal[QuotaType.OBJECT_STORE],
        Field(default=QuotaType.OBJECT_STORE, description="Object storage type"),
    ]
    bytes: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="Number of max usable bytes on all containers (B).",
        ),
    ]
    containers: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of containers allowed for each project.",
        ),
    ]
    objects: Annotated[
        int | None,
        Field(
            default=None,
            ge=-1,
            description="The number of objects allowed for each project.",
        ),
    ]
