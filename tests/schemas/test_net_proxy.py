from typing import Any, Dict

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from tests.schemas.utils import random_ip, random_lower_string


class CaseIpVersion:
    @parametrize(version=["v4", "v6"])
    def case_ip_version(self, version: str) -> str:
        return version


class CaseMissingAttr:
    @parametrize(arg=["ip", "user"])
    def case_missing_arg(self, arg: str) -> str:
        return arg


def private_net_proxy_dict() -> Dict[str, Any]:
    """Dict with PrivateNetProxy minimal attributes."""
    return {"ip": random_ip(), "user": random_lower_string()}


@parametrize_with_cases("ipv", cases=CaseIpVersion)
def test_net_proxy_schema(ipv: str) -> None:
    """Valid PrivateNetProxy schema."""
    d = private_net_proxy_dict()
    d["ip"] = random_ip(version=ipv)
    item = PrivateNetProxy(**d)
    assert item.ip == d.get("ip")
    assert item.user == d.get("user")


@parametrize_with_cases("missing_arg", cases=CaseMissingAttr)
def test_net_proxy_invalid_schema(missing_arg: str) -> None:
    """Create a PrivateNetProxy."""
    d = private_net_proxy_dict()
    d[missing_arg] = None
    with pytest.raises(ValueError):
        PrivateNetProxy(**d)
