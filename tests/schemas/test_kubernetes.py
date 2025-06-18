from typing import Any, Literal

import pytest
from fedreg.v1.provider.enum import ProviderType
from pytest_cases import parametrize_with_cases

from src.models.provider import AuthMethod, Kubernetes, Project, Region
from tests.schemas.utils import (
    auth_method_dict,
    kubernetes_dict,
    project_dict,
    region_dict,
)
from tests.utils import random_lower_string

# TODO: Add BlockStorageVolMap case


class CaseValidAttr:
    def case_regions(self) -> tuple[Literal["regions"], list[Region]]:
        return "regions", [Region(**region_dict())]


class CaseInvalidAttr:
    def case_type(self) -> tuple[Literal["type"], str]:
        return "type", random_lower_string()


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_kubernetes_schema(key: str, value: list[Region] | list[str]) -> None:
    """Valid Kubernetes provider schema."""
    d = kubernetes_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    d[key] = value
    item = Kubernetes(**d)
    assert item.name == d.get("name")
    assert item.type == ProviderType.K8S
    assert item.auth_url == d.get("auth_url")
    projects = d.get("projects", [])
    assert len(item.projects) == len(projects)
    assert item.projects == projects
    identity_providers = d.get("identity_providers", [])
    assert len(item.identity_providers) == len(identity_providers)
    assert item.identity_providers == identity_providers
    regions = d.get("regions", [Region(name="default")])
    assert len(item.regions) == len(regions)
    assert item.regions == regions


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_kubernetes_invalid_schema(key: str, value: Any) -> None:
    """Invalid Kubernetes provider schema.

    Invalid type.
    """
    d = kubernetes_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    d[key] = value
    with pytest.raises(ValueError):
        Kubernetes(**d)
