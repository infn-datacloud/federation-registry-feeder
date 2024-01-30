import pytest
from app.location.schemas import LocationBase
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Region
from tests.schemas.utils import random_country, random_lower_string


@pytest.fixture
def location() -> LocationBase:
    """Fixture with an LocationBase without projects."""
    return LocationBase(site=random_lower_string(), country=random_country())


@parametrize(with_location=[True, False])
def case_with_locations(with_location: bool) -> bool:
    return with_location


@parametrize_with_cases("with_location", cases=".")
def test_region_schema(with_location: bool, location: LocationBase) -> None:
    """Create a UserGroup with or without SLAs."""
    d = {"name": random_lower_string(), "location": location if with_location else None}
    item = Region(**d)
    assert item.name == d.get("name")
    assert item.location == d.get("location")
