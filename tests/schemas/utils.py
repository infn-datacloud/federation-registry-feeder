import ipaddress
import string
import time
from datetime import date
from random import choice, choices, randint, random
from typing import Any
from uuid import UUID, uuid4

from fed_reg.image.enum import ImageOS
from fed_reg.provider.enum import ProviderType
from fed_reg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
    ObjectStoreServiceName,
)
from pycountry import countries
from pydantic import AnyHttpUrl


def random_block_storage_service_name() -> str:
    """Return one of the possible BlockStorageService names."""
    return choice([i.value for i in BlockStorageServiceName])


def random_country() -> str:
    """Return random country."""
    return choice([i.name for i in countries])


def random_compute_service_name() -> str:
    """Return one of the possible ComputeService names."""
    return choice([i.value for i in ComputeServiceName])


def random_date() -> date:
    """Return a random date."""
    d = randint(1, int(time.time()))
    return date.fromtimestamp(d)


def random_float(start: int, end: int) -> float:
    """Return a random float between start and end (included)."""
    return randint(start, end - 1) + random()


def random_identity_service_name() -> str:
    """Return one of the possible IdentityService names."""
    return choice([i.value for i in IdentityServiceName])


def random_image_os_type() -> str:
    """Return one of the possible image OS values."""
    return choice([i.value for i in ImageOS])


def random_ip(
    version: str = "v4",
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if version == "v4":
        return ipaddress.IPv4Address(randint(0, 2**32 - 1))
    elif version == "v6":
        return ipaddress.IPv6Address(randint(0, 2**128 - 1))


def random_lower_string() -> str:
    """Return a generic random string."""
    return "".join(choices(string.ascii_lowercase, k=32))


def random_network_service_name() -> str:
    """Return one of the possible NetworkService names."""
    return choice([i.value for i in NetworkServiceName])


def random_object_store_service_name() -> str:
    """Return one of the possible NetworkService names."""
    return choice([i.value for i in ObjectStoreServiceName])


def random_provider_type(*, exclude: list[str] | None = None) -> str:
    """Return one of the possible provider types."""
    if exclude is None:
        exclude = []
    choices = set([i for i in ProviderType]) - set(exclude)
    return choice(list(choices))


def random_start_end_dates() -> tuple[date, date]:
    """Return a random couples of valid start and end dates (in order)."""
    d1 = random_date()
    d2 = random_date()
    while d1 == d2:
        d2 = random_date()
    if d1 < d2:
        start_date = d1
        end_date = d2
    else:
        start_date = d2
        end_date = d1
    return start_date, end_date


def random_url() -> AnyHttpUrl:
    """Return a random URL."""
    return "https://" + random_lower_string() + ".com"


def auth_method_dict() -> dict[str, Any]:
    """Dict with AuthMethod minimal attributes."""
    return {
        "name": random_lower_string(),
        "protocol": random_lower_string(),
        "endpoint": random_url(),
    }


def issuer_dict() -> dict[str, Any]:
    """Dict with Issuer minimal attributes."""
    return {"issuer": random_url(), "group_claim": random_lower_string()}


def kubernetes_dict() -> dict[str, Any]:
    """Dict with kubernetes provider minimal attributes."""
    return {"name": random_lower_string(), "auth_url": random_url()}


def location_dict() -> dict[str, Any]:
    return {"site": random_lower_string(), "country": random_country()}


def openstack_dict() -> dict[str, Any]:
    """Dict with openstack provider minimal attributes."""
    return {"name": random_lower_string(), "auth_url": random_url()}


def per_region_props_dict() -> dict[str, str]:
    return {"region_name": random_lower_string()}


def private_net_proxy_dict() -> dict[str, Any]:
    """Dict with PrivateNetProxy minimal attributes."""
    return {"host": random_ip(), "user": random_lower_string()}


def project_dict() -> dict[str, UUID]:
    """Dict with Project minimal attributes."""
    return {"id": uuid4(), "sla": uuid4()}


def provider_dict() -> dict[str, Any]:
    """Dict with Provider minimal attributes."""
    return {
        "name": random_lower_string(),
        "type": random_provider_type(),
        "auth_url": random_url(),
    }


def region_dict() -> dict[str, Any]:
    """Dict with Region minimal attributes."""
    return {"name": random_lower_string()}


def sla_dict() -> dict[str, Any]:
    """Dict with SLA minimal attributes."""
    start_date, end_date = random_start_end_dates()
    return {"doc_uuid": uuid4(), "start_date": start_date, "end_date": end_date}


def user_group_dict() -> dict[str, Any]:
    """Dict with UserGroup minimal attributes."""
    return {"name": random_lower_string()}


def urls_dict() -> dict[str, Any]:
    """Return dict for the URLs object."""
    return {
        "flavors": random_url(),
        "identity_providers": random_url(),
        "images": random_url(),
        "locations": random_url(),
        "networks": random_url(),
        "projects": random_url(),
        "providers": random_url(),
        "block_storage_quotas": random_url(),
        "compute_quotas": random_url(),
        "network_quotas": random_url(),
        "object_store_quotas": random_url(),
        "regions": random_url(),
        "block_storage_services": random_url(),
        "compute_services": random_url(),
        "identity_services": random_url(),
        "network_services": random_url(),
        "slas": random_url(),
        "user_groups": random_url(),
    }
