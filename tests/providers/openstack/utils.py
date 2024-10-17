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


def filter_item_by_tags(item: Image | Network, tags: list[str] | None) -> bool:
    """Return true if the item contains any of given tags."""
    valid_tag = tags is None or len(tags) == 0
    if not valid_tag:
        valid_tag = len(set(item.tags).intersection(set(tags))) > 0
    return valid_tag
