from typing import Any, Dict, List, Literal, Tuple
from uuid import UUID, uuid4

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy, Project
from tests.schemas.utils import random_lower_string


class CaseValidAttr:
    def case_default_public_net(self) -> Tuple[Literal["default_public_net"], str]:
        return "default_public_net", random_lower_string()

    def case_default_private_net(self) -> Tuple[Literal["default_private_net"], str]:
        return "default_private_net", random_lower_string()

    def case_private_net_proxy(
        self, net_proxy: PrivateNetProxy
    ) -> Tuple[Literal["private_net_proxy"], PrivateNetProxy]:
        return "private_net_proxy", net_proxy

    def case_per_user_limits(
        self, limits: Limits
    ) -> Tuple[Literal["per_user_limits"], Limits]:
        return "per_user_limits", limits

    def case_per_region_props(
        self, per_region_props: PerRegionProps
    ) -> Tuple[Literal["per_region_props"], List[PerRegionProps]]:
        return "per_region_props", [per_region_props]


class CaseInvalidAttr:
    @parametrize(attr=["id", "sla", "per_user_limits", "per_region_props"])
    def case_none(self, attr: str) -> Tuple[str, None]:
        return attr, None

    def case_single_per_region_props(
        self, per_region_props: PerRegionProps
    ) -> Tuple[Literal["per_region_props"], PerRegionProps]:
        return "per_region_props", per_region_props


def project_dict() -> Dict[str, UUID]:
    """Dict with Project minimal attributes."""
    return {"id": uuid4(), "sla": uuid4()}


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
