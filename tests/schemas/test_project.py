from uuid import uuid4

import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy, Project
from tests.schemas.utils import random_lower_string


@pytest.fixture
def region_props() -> PerRegionProps:
    return PerRegionProps(region_name=random_lower_string())


@case(tags=["valid"])
@parametrize(
    attr=[
        "default_public_net",
        "default_private_net",
        "private_net_proxy",
        "per_user_limits",
        "per_region_props",
    ]
)
def case_valid_attr(attr: str) -> str:
    return attr


@case(tags=["invalid"])
@parametrize(attr=["id", "sla", "per_region_props_none", "per_region_props_single"])
def case_invalid_attr(attr: str) -> str:
    return attr


@parametrize_with_cases("attr", cases=".", has_tag="valid")
def test_project_schema(
    attr: str, net_proxy: PrivateNetProxy, limits: Limits, region_props: PerRegionProps
) -> None:
    """Create an SLA with or without projects."""
    d = {"id": uuid4(), "sla": uuid4()}
    if attr == "default_public_net" or attr == "default_private_net":
        d[attr] = random_lower_string()
    elif attr == "private_net_proxy":
        d[attr] = net_proxy
    elif attr == "per_user_limits":
        d[attr] = limits
    elif attr == "per_region_props":
        d[attr] = [region_props]
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


@parametrize_with_cases("attr", cases=".", has_tag="invalid")
def test_project_invalid_schema(attr: str, region_props: PerRegionProps) -> None:
    """SLA with invalid projects list.

    Duplicated values.
    None value: if the projects key is omitted as in the previous test, by default it
    is an empty list.
    """
    d = {
        "id": None if attr == "id" else uuid4(),
        "sla": None if attr == "sla" else uuid4(),
    }
    if attr == "per_region_props_none":
        d["per_region_props"] = None
    elif attr == "per_region_props_single":
        d["per_region_props"] = region_props
    with pytest.raises(ValueError):
        Project(**d)
