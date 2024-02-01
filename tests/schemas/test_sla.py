from typing import Any, Dict
from uuid import uuid4

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA
from tests.schemas.utils import random_start_end_dates


class CaseWithProjects:
    @parametrize(with_projects=[True, False])
    def case_with_projects(self, with_projects: bool) -> bool:
        return with_projects


def sla_dict() -> Dict[str, Any]:
    """Dict with SLA minimal attributes."""
    start_date, end_date = random_start_end_dates()
    return {"doc_uuid": uuid4(), "start_date": start_date, "end_date": end_date}


@parametrize_with_cases("with_projects", cases=".")
def test_sla_schema(with_projects: bool) -> None:
    """Valid AuthMethod schema.

    With or without projects.
    """
    d = sla_dict()
    if with_projects:
        d["projects"] = [uuid4()]
    item = SLA(**d)
    assert item.doc_uuid == d.get("doc_uuid").hex
    assert item.start_date == d.get("start_date")
    assert item.end_date == d.get("end_date")
    assert item.projects == [i.hex for i in d.get("projects", [])]


@parametrize_with_cases("with_projects", cases=".")
def test_sla_invalid_schema(with_projects: bool) -> None:
    """Invalid SLA schema.

    The projects list contains duplicated values or it received a None value.
    None value: if the projects key is omitted as in the previous test, by default it
    is an empty list.
    """
    proj = uuid4()
    d = sla_dict()
    d["projects"] = [proj, proj] if with_projects else None
    with pytest.raises(ValueError):
        SLA(**d)
