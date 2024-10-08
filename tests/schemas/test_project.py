from typing import Any, Literal

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy, Project
from tests.schemas.utils import (
    per_region_props_dict,
    private_net_proxy_dict,
    project_dict,
    random_lower_string,
)


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

    def case_per_region_props(
        self,
    ) -> tuple[Literal["per_region_props"], list[PerRegionProps]]:
        return "per_region_props", [PerRegionProps(**per_region_props_dict())]


class CaseInvalidAttr:
    @parametrize(attr=["id", "sla", "per_user_limits", "per_region_props"])
    def case_none(self, attr: str) -> tuple[str, None]:
        return attr, None

    def case_single_per_region_props(
        self,
    ) -> tuple[Literal["per_region_props"], PerRegionProps]:
        return "per_region_props", PerRegionProps(**per_region_props_dict())


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_project_schema(key: str, value: Any) -> None:
    """Valid Project schema.

    Validate optional attributes. Check default values.
    """
    d = project_dict()
    d[key] = value
    item = Project(**d)
    assert item.id == d.get("id").hex
    assert item.sla == d.get("sla").hex
    assert item.default_public_net == d.get("default_public_net")
    assert item.default_private_net == d.get("default_private_net")
    assert item.private_net_proxy == d.get("private_net_proxy")
    assert item.per_user_limits == d.get("per_user_limits", Limits())
    per_region_props = d.get("per_region_props", [])
    assert len(item.per_region_props) == len(per_region_props)
    assert item.per_region_props == per_region_props


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_project_invalid_schema(key: str, value: Any) -> None:
    """Invalid Project schema.

    None values when not allowed and single value instead of a list.
    """
    d = project_dict()
    d[key] = value
    with pytest.raises(ValueError):
        Project(**d)
