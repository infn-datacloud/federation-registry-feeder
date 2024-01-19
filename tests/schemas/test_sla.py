from uuid import uuid4

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA
from tests.schemas.utils import random_start_end_dates


@parametrize(with_projects=[True, False])
def case_with_projects(with_projects: bool) -> bool:
    return with_projects


@parametrize_with_cases("with_projects", cases=".")
def test_sla_schema(with_projects: bool) -> None:
    """Create an SLA with or without projects."""
    start_date, end_date = random_start_end_dates()
    d = {"doc_uuid": uuid4(), "start_date": start_date, "end_date": end_date}
    if with_projects:
        d["projects"] = [uuid4()]
    item = SLA(**d)
    assert item.doc_uuid == d.get("doc_uuid").hex
    assert item.start_date == d.get("start_date")
    assert item.end_date == d.get("end_date")
    assert item.projects == [i.hex for i in d.get("projects", [])]


@parametrize_with_cases("with_projects", cases=".")
def test_sla_invalid_schema(with_projects: bool) -> None:
    """SLA with invalid projects list.

    Duplicated values.
    None value: if the projects key is omitted as in the previous test, by default it
    is an empty list.
    """
    start_date, end_date = random_start_end_dates()
    proj = uuid4()
    d = {
        "doc_uuid": uuid4(),
        "start_date": start_date,
        "end_date": end_date,
        "projects": [proj, proj] if with_projects else None,
    }
    with pytest.raises(ValueError):
        SLA(**d)
