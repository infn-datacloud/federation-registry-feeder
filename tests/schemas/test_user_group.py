import pytest
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import SLA, UserGroup
from tests.schemas.utils import sla_dict, user_group_dict


class CaseInvalidSLA:
    def case_none(self) -> None:
        return None

    def case_duplicated_slas(self) -> list[SLA]:
        item1 = SLA(**sla_dict())
        item2 = SLA(**{**sla_dict(), "doc_uuid": item1.doc_uuid})
        return [item1, item2]


def test_user_group_schema() -> None:
    """Valid UserGroup schema with one SLA."""
    d = user_group_dict()
    d["slas"] = [SLA(**sla_dict())]
    item = UserGroup(**d)
    assert item.name == d.get("name")
    slas = d.get("slas", [])
    assert len(item.slas) == len(slas)
    assert item.slas == slas


@parametrize_with_cases("slas", cases=CaseInvalidSLA)
def test_user_group_invalid_schema(slas: list[SLA] | None) -> None:
    """Invalid UserGroup schema.

    The SLA list contains duplicate SLA values or it received a None value.
    None value: if the slas key is omitted as in the previous test, by default it
    is an empty list.
    """
    d = user_group_dict()
    d["slas"] = slas
    with pytest.raises(ValueError):
        UserGroup(**d)
