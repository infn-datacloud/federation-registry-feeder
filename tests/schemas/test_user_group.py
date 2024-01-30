import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, UserGroup
from tests.schemas.utils import random_lower_string


@parametrize(with_slas=[True, False])
def case_with_slas(with_slas: bool) -> bool:
    return with_slas


def test_user_group_schema(sla: SLA) -> None:
    """Create a UserGroup with or without SLAs."""
    d = {"name": random_lower_string(), "slas": [sla]}
    item = UserGroup(**d)
    assert item.name == d.get("name")
    slas = d.get("slas", [])
    assert len(item.slas) == len(slas)
    assert item.slas == slas


@parametrize_with_cases("with_slas", cases=".")
def test_user_group_invalid_schema(with_slas: bool, sla: SLA) -> None:
    """SLA with invalid slas list.

    Duplicated values: SLA with same doc_uuid.
    None value: if the SLAs key is omitted as in the previous test, by default it
    is an empty list.
    """
    d = {"name": random_lower_string(), "slas": [sla, sla] if with_slas else None}
    with pytest.raises(ValueError):
        UserGroup(**d)
