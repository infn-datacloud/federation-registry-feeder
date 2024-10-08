from uuid import UUID, uuid4

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA
from tests.schemas.utils import sla_dict


class CaseWithProjects:
    @parametrize(with_projects=[True, False])
    def case_with_projects(self, with_projects: bool) -> bool:
        return with_projects


class CaseInvalidProject:
    def case_none(self) -> None:
        return None

    def case_duplicated_project(self) -> list[UUID]:
        v = uuid4()
        return [v, v]


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


@parametrize_with_cases("projects", cases=CaseInvalidProject)
def test_sla_invalid_schema(projects: list[UUID] | None) -> None:
    """Invalid SLA schema.

    The projects list contains duplicated values or it received a None value.
    None value: if the projects key is omitted as in the previous test, by default it
    is an empty list.
    """
    d = sla_dict()
    d["projects"] = projects
    with pytest.raises(ValueError):
        SLA(**d)
