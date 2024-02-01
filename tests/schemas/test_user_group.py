from typing import Any, Dict

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, UserGroup
from tests.schemas.utils import random_lower_string


class CaseWithSLAs:
    @parametrize(with_slas=[True, False])
    def case_with_slas(self, with_slas: bool) -> bool:
        return with_slas


def user_group_dict() -> Dict[str, Any]:
    """Dict with UserGroup minimal attributes."""
    return {"name": random_lower_string()}


def test_user_group_schema(sla: SLA) -> None:
    """Valid UserGroup schema with one SLA."""
    d = user_group_dict()
    d["slas"] = [sla]
    item = UserGroup(**d)
    assert item.name == d.get("name")
    slas = d.get("slas", [])
    assert len(item.slas) == len(slas)
    assert item.slas == slas


@parametrize_with_cases("with_slas", cases=CaseWithSLAs)
def test_user_group_invalid_schema(with_slas: bool, sla: SLA) -> None:
    """Invalid UserGroup schema.

    The SLA list contains duplicate SLA values or it received a None value.
    None value: if the slas key is omitted as in the previous test, by default it
    is an empty list.
    """
    d = user_group_dict()
    d["slas"] = [sla, sla] if with_slas else None
    with pytest.raises(ValueError):
        UserGroup(**d)
