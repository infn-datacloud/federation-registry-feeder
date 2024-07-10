from typing import Any, Literal, Tuple

import pytest
from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import ProviderSiblings


class CaseInvalidAttr:
    @parametrize(attr=["identity_provider", "project", "region"])
    def case_none(self, attr: str) -> Tuple[str, None]:
        return attr, None

    def case_idp_list(
        self, identity_provider_create: IdentityProviderCreateExtended
    ) -> Tuple[Literal["identity_provider"], list[IdentityProviderCreateExtended]]:
        return "identity_provider", [identity_provider_create]

    def case_project_list(
        self, project_create: ProjectCreate
    ) -> Tuple[Literal["project"], list[ProjectCreate]]:
        return "project", [project_create]

    def case_region_list(
        self, region_create: RegionCreateExtended
    ) -> Tuple[Literal["region"], list[RegionCreateExtended]]:
        return "region", [region_create]


def test_provider_schema(
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
) -> None:
    """Valid Provider schema with or without regions."""
    d = {
        "identity_provider": identity_provider_create,
        "project": project_create,
        "region": region_create,
    }
    item = ProviderSiblings(**d)
    assert item.identity_provider == identity_provider_create
    assert item.project == project_create
    assert item.region == region_create


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_provider_invalid_schema(
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
    key: str,
    value: Any,
) -> None:
    """Invalid Provider schema.

    Missing required values and lists instead of single values.
    """
    d = {
        "identity_provider": identity_provider_create,
        "project": project_create,
        "region": region_create,
    }
    d[key] = value
    with pytest.raises(ValueError):
        ProviderSiblings(**d)
