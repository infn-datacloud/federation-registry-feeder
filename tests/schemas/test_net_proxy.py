from ipaddress import IPv4Address, IPv6Address

import pytest
from pydantic import IPvAnyAddress
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from tests.schemas.utils import private_net_proxy_dict
from tests.utils import random_ip, random_lower_string


class CaseHost:
    @parametrize(version=["v4", "v6"])
    def case_ip_version(self, version: str) -> IPv4Address | IPv6Address:
        return random_ip(version=version)

    def case_string(self) -> str:
        return random_lower_string()


class CaseMissingAttr:
    @parametrize(arg=["host", "user"])
    def case_missing_arg(self, arg: str) -> str:
        return arg


@parametrize_with_cases("host", cases=CaseHost)
def test_net_proxy_schema(host: IPvAnyAddress | str) -> None:
    """Valid PrivateNetProxy schema."""
    d = private_net_proxy_dict()
    d["host"] = host
    item = PrivateNetProxy(**d)
    assert item.host == d.get("host")
    assert item.user == d.get("user")


@parametrize_with_cases("missing_arg", cases=CaseMissingAttr)
def test_net_proxy_invalid_schema(missing_arg: str) -> None:
    """Create a PrivateNetProxy."""
    d = private_net_proxy_dict()
    d[missing_arg] = None
    with pytest.raises(ValueError):
        PrivateNetProxy(**d)
