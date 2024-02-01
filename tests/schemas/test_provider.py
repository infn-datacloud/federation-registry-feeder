import copy
from typing import Any, Dict, List, Literal, Tuple
from uuid import uuid4

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import AuthMethod, Project, Provider, Region
from tests.schemas.utils import random_lower_string, random_provider_type, random_url


class CaseValidAttr:
    def case_regions(self, region: Region) -> Tuple[Literal["regions"], List[Region]]:
        return "regions", [region]

    # TODO: Add BlockStorageVolMap case


class CaseInvalidAttr:
    @parametrize(attr=["auth_url", "identity_providers", "projects", "regions"])
    def case_none(self, attr: str) -> Tuple[str, None]:
        return attr, None

    def case_single_auth_method(
        self, auth_method: AuthMethod
    ) -> Tuple[Literal["identity_providers"], AuthMethod]:
        return "identity_providers", auth_method

    def case_single_project(
        self, project: Project
    ) -> Tuple[Literal["projects"], Project]:
        return "projects", project

    def case_single_region(self, region: Region) -> Tuple[Literal["regions"], Region]:
        return "regions", region

    @parametrize(diff_attr=["endpoint", "idp_name"])
    def case_duplicated_auth_methods(
        self, diff_attr: str, auth_method: AuthMethod
    ) -> Tuple[Literal["identity_providers"], AuthMethod]:
        auth_method2 = copy.deepcopy(auth_method)
        if diff_attr == "endpoint":
            auth_method2.endpoint = random_url()
        elif diff_attr == "idp_name":
            auth_method2.idp_name = random_lower_string()
        return "identity_providers", [auth_method, auth_method2]

    @parametrize(diff_attr=["id", "sla"])
    def case_duplicated_projects(
        self, diff_attr: str, project: Project
    ) -> Tuple[Literal["projects"], Project]:
        project2 = copy.deepcopy(project)
        if diff_attr == "endpoint":
            project2.id = uuid4()
        elif diff_attr == "idp_name":
            project2.sla = uuid4()
        return "projects", [project, project2]

    def case_duplicated_regions(
        self, region: Region
    ) -> Tuple[Literal["regions"], Region]:
        return "regions", [region, region]


def provider_dict() -> Dict[str, Any]:
    """Dict with Provider minimal attributes."""
    return {
        "name": random_lower_string(),
        "type": random_provider_type(),
        "auth_url": random_url(),
    }


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_provider_schema(
    auth_method: AuthMethod, project: Project, key: str, value: Any
) -> None:
    """Valid Provider schema with or without regions."""
    d = provider_dict()
    d["identity_providers"] = [auth_method]
    d["projects"] = [project]
    d[key] = value
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
def test_provider_invalid_schema(
    auth_method: AuthMethod, project: Project, key: str, value: Any
) -> None:
    """Invalid Provider schema.

    Missing required values, duplicated values and single values instead of lists.
    """
    d = provider_dict()
    d["identity_providers"] = [auth_method]
    d["projects"] = [project]
    d[key] = value
    with pytest.raises(ValueError):
        Provider(**d)
