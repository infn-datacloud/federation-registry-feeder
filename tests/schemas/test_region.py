from typing import Optional

import pytest
from app.location.schemas import LocationBase
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Region
from tests.schemas.utils import random_country, random_lower_string


@pytest.fixture
def location() -> LocationBase:
    """Fixture with an LocationBase without projects."""
    return LocationBase(site=random_lower_string(), country=random_country())


class CaseLocation:
    @parametrize(with_location=[True, False])
    def case_with_locations(self, with_location: bool, location: LocationBase) -> bool:
        return location if with_location else None


@parametrize_with_cases("location", cases=CaseLocation)
def test_region_schema(location: Optional[LocationBase]) -> None:
    """Valid Region schema."""
    d = {"name": random_lower_string(), "location": location}
    item = Region(**d)
    assert item.name == d.get("name")
    assert item.location == d.get("location")
