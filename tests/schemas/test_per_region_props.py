import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy
from tests.schemas.utils import random_ip, random_lower_string


@pytest.fixture
def limits() -> Limits:
    return Limits()


@pytest.fixture
def net_proxy() -> PrivateNetProxy:
    return PrivateNetProxy(ip=random_ip(), user=random_lower_string())


@parametrize(attr=["private_net_proxy", "per_user_limits"])
def case_net_proxy(attr: bool) -> bool:
    return attr


@parametrize_with_cases("attr", cases=".")
def test_net_proxy_schema(
    attr: str, limits: Limits, net_proxy: PrivateNetProxy
) -> None:
    """Create a PerRegionProps."""
    d = {
        "region_name": random_lower_string(),
        "default_public_net": random_lower_string(),
        "default_private_net": random_lower_string(),
        "private_net_proxy": net_proxy if attr == "private_net_proxy" else None,
        "per_user_limits": limits if attr == "per_user_limits" else None,
    }
    item = PerRegionProps(**d)
    assert item.region_name == d.get("region_name")
    assert item.default_public_net == d.get("default_public_net")
    assert item.default_private_net == d.get("default_private_net")
    assert item.private_net_proxy == d.get("private_net_proxy")
    assert item.per_user_limits == d.get("per_user_limits")


def test_per_region_props_invalid_schema() -> None:
    """Create a PrivateNetProxy."""
    with pytest.raises(ValueError):
        PerRegionProps()
