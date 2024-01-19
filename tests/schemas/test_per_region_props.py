import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy
from tests.schemas.utils import random_ip, random_lower_string


@pytest.fixture
def limits() -> Limits:
    return Limits()


@pytest.fixture
def net_proxy() -> PrivateNetProxy:
    return PrivateNetProxy(ip=random_ip("v4"), user=random_lower_string())


@case(tags="limit")
@parametrize(with_limits=[True, False])
def case_with_limits(with_limits: bool) -> bool:
    return with_limits


@case(tags="net_proxy")
@parametrize(with_net_proxy=[True, False])
def case_net_proxy(with_net_proxy: bool) -> bool:
    return with_net_proxy


@parametrize_with_cases("with_limits", cases=".", has_tag="limit")
@parametrize_with_cases("with_net_proxy", cases=".", has_tag="net_proxy")
def test_net_proxy_schema(
    with_limits: bool, with_net_proxy: bool, limits: Limits, net_proxy: PrivateNetProxy
) -> None:
    """Create a PerRegionProps."""
    d = {
        "region_name": random_lower_string(),
        "default_public_net": random_lower_string(),
        "default_private_net": random_lower_string(),
        "private_net_proxy": net_proxy if with_net_proxy else None,
        "per_user_limits": limits if with_limits else None,
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
