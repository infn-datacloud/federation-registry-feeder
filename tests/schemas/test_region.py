from fedreg.location.schemas import LocationBase
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Region
from tests.schemas.utils import location_dict, region_dict


class CaseLocation:
    @parametrize(with_location=[True, False])
    def case_with_locations(self, with_location: bool) -> bool:
        return LocationBase(**location_dict()) if with_location else None


@parametrize_with_cases("location", cases=CaseLocation)
def test_region_schema(location: LocationBase | None) -> None:
    """Valid Region schema."""
    d = {**region_dict(), "location": location}
    item = Region(**d)
    assert item.name == d.get("name")
    assert item.location == d.get("location")
