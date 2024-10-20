from typing import Literal

import pytest
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy
from tests.schemas.utils import per_region_props_dict, private_net_proxy_dict
from tests.utils import random_lower_string


class CaseValidAttr:
    def case_default_public_net(self) -> tuple[Literal["default_public_net"], str]:
        return "default_public_net", random_lower_string()

    def case_default_private_net(self) -> tuple[Literal["default_private_net"], str]:
        return "default_private_net", random_lower_string()

    def case_private_net_proxy(
        self,
    ) -> tuple[Literal["private_net_proxy"], PrivateNetProxy]:
        return "private_net_proxy", PrivateNetProxy(**private_net_proxy_dict())

    def case_per_user_limits(self) -> tuple[Literal["per_user_limits"], Limits]:
        return "per_user_limits", Limits()


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_net_proxy_schema(
    key: str,
    value: PrivateNetProxy | PerRegionProps | str,
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
