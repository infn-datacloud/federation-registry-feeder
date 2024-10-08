import pytest
from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
)
from pytest_cases import parametrize_with_cases

from src.models.provider import ProviderSiblings


class CaseInvalidIdp:
    def case_none(self) -> None:
        return None

    def case_idp_list(
        self, identity_provider_create: IdentityProviderCreateExtended
    ) -> list[IdentityProviderCreateExtended]:
        return [identity_provider_create]


class CaseInvalidProject:
    def case_none(self) -> None:
        return None

    def case_project_list(self, project_create: ProjectCreate) -> list[ProjectCreate]:
        return [project_create]


class CaseInvalidRegion:
    def case_none(self) -> None:
        return None

    def case_region_list(
        self, region_create: RegionCreateExtended
    ) -> list[RegionCreateExtended]:
        return [region_create]


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


@parametrize_with_cases("value", cases=CaseInvalidIdp)
def test_provider_invalid_idp(
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
    value: IdentityProviderCreateExtended,
) -> None:
    """Invalid Provider schema.

    Missing required values and lists instead of single values.
    """
    d = {
        "identity_provider": value,
        "project": project_create,
        "region": region_create,
    }
    with pytest.raises(ValueError):
        ProviderSiblings(**d)


@parametrize_with_cases("value", cases=CaseInvalidProject)
def test_provider_invalid_project(
    identity_provider_create: IdentityProviderCreateExtended,
    region_create: RegionCreateExtended,
    value: ProjectCreate,
) -> None:
    """Invalid Provider schema.

    Missing required values and lists instead of single values.
    """
    d = {
        "identity_provider": identity_provider_create,
        "project": value,
        "region": region_create,
    }
    with pytest.raises(ValueError):
        ProviderSiblings(**d)


@parametrize_with_cases("value", cases=CaseInvalidRegion)
def test_provider_invalid_region(
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    value: RegionCreateExtended,
) -> None:
    """Invalid Provider schema.

    Missing required values and lists instead of single values.
    """
    d = {
        "identity_provider": identity_provider_create,
        "project": project_create,
        "region": value,
    }
    with pytest.raises(ValueError):
        ProviderSiblings(**d)
