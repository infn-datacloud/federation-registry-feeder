from uuid import uuid4

from fedreg.provider.schemas_extended import (
    FlavorCreateExtended,
    ImageCreateExtended,
    NetworkCreateExtended,
)
from pytest_cases import parametrize_with_cases

from src.utils import get_updated_resources
from tests.utils import random_lower_string


class CaseResources:
    def case_flavors(self) -> list[FlavorCreateExtended]:
        return [
            FlavorCreateExtended(name=random_lower_string(), uuid=uuid4()),
            FlavorCreateExtended(name=random_lower_string(), uuid=uuid4()),
            FlavorCreateExtended(name=random_lower_string(), uuid=uuid4()),
        ]

    def case_images(self) -> list[ImageCreateExtended]:
        return [
            ImageCreateExtended(name=random_lower_string(), uuid=uuid4()),
            ImageCreateExtended(name=random_lower_string(), uuid=uuid4()),
            ImageCreateExtended(name=random_lower_string(), uuid=uuid4()),
        ]

    def case_networks(self) -> list[NetworkCreateExtended]:
        return [
            NetworkCreateExtended(name=random_lower_string(), uuid=uuid4()),
            NetworkCreateExtended(name=random_lower_string(), uuid=uuid4()),
            NetworkCreateExtended(name=random_lower_string(), uuid=uuid4()),
        ]


@parametrize_with_cases("resources", cases=CaseResources)
def test_identical_resources(
    resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources[0:1]
    update_resources = get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 1


@parametrize_with_cases("resources", cases=CaseResources)
def test_add_new_resources(
    resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources[1:]
    update_resources = get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 3


@parametrize_with_cases("resources", cases=CaseResources)
def test_add_only_new_resources(
    resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources
    update_resources = get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 3
