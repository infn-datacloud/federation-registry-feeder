from typing import Any
from uuid import UUID, uuid4

from tests.fed_reg.utils import (
    random_country,
    random_provider_type,
    random_start_end_dates,
)
from tests.utils import random_ip, random_lower_string, random_url


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
