from typing import Any

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import AuthMethod, Project, Provider, Region
from tests.schemas.utils import (
    auth_method_dict,
    project_dict,
    provider_dict,
    region_dict,
)

# TODO: Add BlockStorageVolMap case


class CaseValidRegions:
    def case_none(self) -> None:
        return None

    def case_regions(self) -> list[Region]:
        return [Region(**region_dict())]


class CaseInvalidAttr:
    @parametrize(attr=("auth_url",))
    def case_missing_attr(self, attr: str) -> tuple[str, None]:
        return attr, None


class CaseInvalidRegions:
    def case_none(self) -> None:
        return None

    def case_single_region(self) -> Region:
        return Region(**region_dict())

    def case_duplicated_regions(self) -> list[Region]:
        item1 = Region(**region_dict())
        item2 = Region(**{**region_dict(), "name": item1.name})
        return [item1, item2]


class CaseInvalidProjects:
    def case_none(self) -> None:
        return None

    def case_single_project(self) -> Project:
        return Project(**project_dict())

    @parametrize(attr=["id", "sla"])
    def case_duplicated_projects(self, attr: str) -> list[Project]:
        item1 = Project(**project_dict())
        item2 = Project(**project_dict())
        item2.__setattr__(attr, item1.__getattribute__(attr))
        return [item1, item2]


class CaseInvalidAuthMethods:
    def case_none(self) -> None:
        return None

    def case_single_auth_method(self) -> AuthMethod:
        return AuthMethod(**auth_method_dict())

    @parametrize(attr=["endpoint", "idp_name"])
    def case_duplicated_auth_methods(self, attr: str) -> list[AuthMethod]:
        item1 = AuthMethod(**auth_method_dict())
        item2 = AuthMethod(**auth_method_dict())
        item2.__setattr__(attr, item1.__getattribute__(attr))
        return [item1, item2]


@parametrize_with_cases("region", cases=CaseValidRegions)
def test_provider_schema(region: Region) -> None:
    """Valid Provider schema with or without regions."""
    d = provider_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    if region:
        d["regions"] = region
    item = Provider(**d)
    assert item.name == d.get("name")
    assert item.type == d.get("type").value
    assert item.auth_url == d.get("auth_url")
    projects = d.get("projects", [])
    assert len(item.projects) == len(projects)
    assert item.projects == projects
    identity_providers = d.get("identity_providers", [])
    assert len(item.identity_providers) == len(identity_providers)
    assert item.identity_providers == identity_providers
    regions = d.get("regions", [])
    assert len(item.regions) == len(regions)
    assert item.regions == regions


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_provider_invalid_attrs(key: str, value: Any) -> None:
    """Invalid Provider schema.

    Missing required values, duplicated values and single values instead of lists.
    """
    d = provider_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    d[key] = value
    with pytest.raises(ValueError):
        Provider(**d)


@parametrize_with_cases("value", cases=CaseInvalidAuthMethods)
def test_provider_invalid_auth_methods(value: list[AuthMethod] | None) -> None:
    """Invalid Provider schema.

    Missing required values, duplicated values and single values instead of lists.
    """
    d = provider_dict()
    d["identity_providers"] = value
    d["projects"] = [Project(**project_dict())]
    with pytest.raises(ValueError):
        Provider(**d)


@parametrize_with_cases("value", cases=CaseInvalidProjects)
def test_provider_invalid_projects(value: list[Project] | None) -> None:
    """Invalid Provider schema.

    Missing required values, duplicated values and single values instead of lists.
    """
    d = provider_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = value
    with pytest.raises(ValueError):
        Provider(**d)


@parametrize_with_cases("value", cases=CaseInvalidRegions)
def test_provider_invalid_regions(value: list[Region] | None) -> None:
    """Invalid Provider schema.

    Missing required values, duplicated values and single values instead of lists.
    """
    d = provider_dict()
    d["identity_providers"] = [AuthMethod(**auth_method_dict())]
    d["projects"] = [Project(**project_dict())]
    d["regions"] = value
    with pytest.raises(ValueError):
        Provider(**d)
