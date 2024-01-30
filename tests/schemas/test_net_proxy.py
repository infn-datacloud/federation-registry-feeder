import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from tests.schemas.utils import random_ip, random_lower_string


@case(tags="ip_version")
@parametrize(version=["v4", "v6"])
def case_ip_ver(version: str) -> str:
    return version


@case(tags="missing")
@parametrize(arg=["ip", "user"])
def case_missing_arg(arg: str) -> str:
    return arg


@parametrize_with_cases("ipv", cases=".", has_tag="ip_version")
def test_net_proxy_schema(ipv: str) -> None:
    """Create a PrivateNetProxy."""
    d = {"ip": random_ip(version=ipv), "user": random_lower_string()}
    item = PrivateNetProxy(**d)
    assert item.ip == d.get("ip")
    assert item.user == d.get("user")


@parametrize_with_cases("missing_arg", cases=".", has_tag="missing")
def test_net_proxy_invalid_schema(missing_arg: str) -> None:
    """Create a PrivateNetProxy."""
    d = {
        "ip": None if missing_arg == "ip" else random_ip(),
        "user": None if missing_arg == "user" else random_lower_string(),
    }
    with pytest.raises(ValueError):
        PrivateNetProxy(**d)
