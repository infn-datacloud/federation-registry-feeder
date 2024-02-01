from typing import Dict, Literal, Optional, Tuple, Union

import pytest
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy
from tests.schemas.utils import random_lower_string


class CaseValidAttr:
    def case_private_net_proxy(
        self, net_proxy: PrivateNetProxy
    ) -> Tuple[Literal["private_net_proxy"], PrivateNetProxy]:
        return "private_net_proxy", net_proxy

    def case_per_user_limits(
        self, limits: Limits
    ) -> Tuple[Literal["per_user_limits"], Limits]:
        return "per_user_limits", limits


def per_region_props_dict() -> Dict[str, str]:
    return {
        "region_name": random_lower_string(),
        "default_public_net": random_lower_string(),
        "default_private_net": random_lower_string(),
    }


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_net_proxy_schema(
    key: str,
    value: Optional[Union[PrivateNetProxy, PerRegionProps]],
) -> None:
    """Valid PerRegionProps schema."""
    d = per_region_props_dict()
    d[key] = value
    item = PerRegionProps(**d)
    assert item.region_name == d.get("region_name")
    assert item.default_public_net == d.get("default_public_net")
    assert item.default_private_net == d.get("default_private_net")
    assert item.private_net_proxy == d.get("private_net_proxy")
    assert item.per_user_limits == d.get("per_user_limits", Limits())


def test_per_region_props_invalid_schema() -> None:
    """Invalid PerRegionProps schema.

    Region name is required.
    """
    with pytest.raises(ValueError):
        PerRegionProps()
