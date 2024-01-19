import time
from datetime import date
from random import randint
from typing import Tuple
from uuid import uuid4

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import SLA


def random_date() -> date:
    """Return a random date."""
    d = randint(1, int(time.time()))
    return date.fromtimestamp(d)


def random_start_end_dates() -> Tuple[date, date]:
    """Return a random couples of valid start and end dates (in order)."""
    d1 = random_date()
    d2 = random_date()
    while d1 == d2:
        d2 = random_date()
    if d1 < d2:
        start_date = d1
        end_date = d2
    else:
        start_date = d2
        end_date = d1
    return start_date, end_date


@parametrize(with_projects=[True, False])
def case_with_projects(with_projects: bool) -> bool:
    return with_projects


@parametrize_with_cases("with_projects", cases=".")
def test_sla_schema(with_projects: bool) -> None:
    """Create an SLA with or without projects"""
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
    d = {"doc_uuid": uuid4(), "start_date": start_date, "end_date": end_date}
    if with_projects:
        proj = uuid4()
        d["projects"] = [proj, proj]
    else:
        d["projects"] = None
    with pytest.raises(ValueError):
        SLA(**d)
