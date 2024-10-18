from random import choice, getrandbits, randint
from typing import Any
from uuid import uuid4

from openstack.image.v2.image import Image
from openstack.network.v2.network import Network

from tests.schemas.utils import random_float, random_image_os_type, random_lower_string


def random_image_status(*, exclude: list[str] | None = None) -> str:
    """Return one of the possible image status types."""
    if exclude is None:
        exclude = []
    choices = set(
        [
            "queued",
            "saving",
            "uploading",
            "importing",
            "active",
            "deactivated",
            "killed",
            "deleted",
            "pending_delete",
        ]
    ) - set(exclude)
    return choice(list(choices))


def random_image_visibility(*, exclude: list[str] | None = None) -> str:
    """Return one of the possible image visibility types."""
    if exclude is None:
        exclude = []
    choices = set(["public", "private", "shared", "community"]) - set(exclude)
    return choice(list(choices))


def random_network_status(*, exclude: list[str] | None = None) -> str:
    """Return one of the possible network status types."""
    if exclude is None:
        exclude = []
    choices = set(["active", "build", "down", "error"]) - set(exclude)
    return choice(list(choices))


def openstack_flavor_dict() -> dict[str, Any]:
    """dict with flavor minimal data."""
    return {
        "name": random_lower_string(),
        "disk": randint(0, 100),
        "is_public": getrandbits(1),
        "ram": randint(0, 100),
        "vcpus": randint(0, 100),
        "swap": randint(0, 100),
        "ephemeral": randint(0, 100),
        "is_disabled": False,
        "rxtx_factor": random_float(0, 100),
        "extra_specs": {},
    }


def openstack_image_dict() -> dict[str, Any]:
    """dict with image minimal data."""
    return {
        "id": uuid4().hex,
        "name": random_lower_string(),
        "status": "active",
        "owner_id": uuid4().hex,
        "os_type": random_image_os_type(),
        "os_distro": random_lower_string(),
        "os_version": random_lower_string(),
        "architecture": random_lower_string(),
        "kernel_id": random_lower_string(),
        "visibility": "public",
    }


def openstack_network_dict() -> dict[str, Any]:
    """dict with network minimal data."""
    return {
        "id": uuid4().hex,
        "name": random_lower_string(),
        "status": "active",
        "project_id": uuid4().hex,
        "is_router_external": getrandbits(1),
        "is_shared": False,
        "mtu": randint(1, 100),
    }


def openstack_block_storage_quotas_dict() -> dict[str, int]:
    """dict with the block storage quotas attributes."""
    return {
        "backup_gigabytes": randint(0, 100),
        "backups": randint(0, 100),
        "gigabytes": randint(0, 100),
        "groups": randint(0, 100),
        "per_volume_gigabytes": randint(0, 100),
        "snapshots": randint(0, 100),
        "volumes": randint(0, 100),
    }


def openstack_compute_quotas_dict() -> dict[str, int]:
    """dict with the compute quotas attributes."""
    return {
        "cores": randint(0, 100),
        "fixed_ips": randint(0, 100),
        "floating_ips": randint(0, 100),
        "injected_file_content_bytes": randint(0, 100),
        "injected_file_path_bytes": randint(0, 100),
        "injected_files": randint(0, 100),
        "instances": randint(0, 100),
        "key_pairs": randint(0, 100),
        "metadata_items": randint(0, 100),
        "networks": randint(0, 100),
        "ram": randint(0, 100),
        "security_group_rules": randint(0, 100),
        "security_groups": randint(0, 100),
        "server_groups": randint(0, 100),
        "server_group_members": randint(0, 100),
        "force": False,
    }


def openstack_network_quotas_dict() -> dict[str, int]:
    """dict with the network quotas attributes."""
    return {
        # "check_limit": False,
        "floating_ips": randint(0, 100),
        "health_monitors": randint(0, 100),
        "listeners": randint(0, 100),
        "load_balancers": randint(0, 100),
        "l7_policies": randint(0, 100),
        "networks": randint(0, 100),
        "pools": randint(0, 100),
        "ports": randint(0, 100),
        # "project_id": ?,
        "rbac_policies": randint(0, 100),
        "routers": randint(0, 100),
        "subnets": randint(0, 100),
        "subnet_pools": randint(0, 100),
        "security_group_rules": randint(0, 100),
        "security_groups": randint(0, 100),
    }


def openstack_object_store_headers() -> dict[str, int]:
    return {
        "X-Account-Bytes-Used": randint(0, 100),
        "X-Account-Container-Count": randint(0, 100),
        "X-Account-Object-Count": randint(0, 100),
        "X-Account-Meta-Quota-Bytes": randint(0, 100),
    }


def filter_item_by_tags(item: Image | Network, tags: list[str] | None) -> bool:
    """Return true if the item contains any of given tags."""
    valid_tag = tags is None or len(tags) == 0
    if not valid_tag:
        valid_tag = len(set(item.tags).intersection(set(tags))) > 0
    return valid_tag
