from typing import Any, Literal

import pytest
from fedreg.v1.provider.enum import ProviderType
from pytest_cases import parametrize_with_cases

from src.models.provider import AuthMethod, Openstack, Project, Region
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    project_dict,
    region_dict,
)
from tests.utils import random_lower_string

# TODO: Add BlockStorageVolMap case


class CaseValidAttr:
    def case_regions(self) -> tuple[Literal["regions"], list[Region]]:
        return "regions", [Region(**region_dict())]

    def case_image_tags(self) -> tuple[Literal["image_tags"], list[str]]:
        return "image_tags", [random_lower_string()]

    def case_network_tags(self) -> tuple[Literal["network_tags"], list[str]]:
        return "network_tags", [random_lower_string()]


class CaseInvalidAttr:
    def case_type(self) -> tuple[Literal["type"], str]:
        return "type", random_lower_string()


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_openstack_schema(key: str, value: list[Region] | list[str]) -> None:
    """Valid Openstack provider schema."""
    d = openstack_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    d[key] = value
    item = Openstack(**d)
    assert item.name == d.get("name")
    assert item.type == ProviderType.OS
    assert item.auth_url == d.get("auth_url")
    projects = d.get("projects", [])
    assert len(item.projects) == len(projects)
    assert item.projects == projects
    identity_providers = d.get("identity_providers", [])
    assert len(item.identity_providers) == len(identity_providers)
    assert item.identity_providers == identity_providers
    regions = d.get("regions", [Region(name="RegionOne")])
    assert len(item.regions) == len(regions)
    assert item.regions == regions
    image_tags = d.get("image_tags", [])
    assert len(item.image_tags) == len(image_tags)
    assert item.image_tags == image_tags
    network_tags = d.get("network_tags", [])
    assert len(item.network_tags) == len(network_tags)
    assert item.network_tags == network_tags


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_openstack_invalid_schema(key: str, value: Any) -> None:
    """Invalid Openstack provider schema.

    Invalid type.
    """
    d = openstack_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    d[key] = value
    with pytest.raises(ValueError):
        Openstack(**d)
