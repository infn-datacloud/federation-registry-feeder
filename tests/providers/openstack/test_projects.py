from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

import pytest
from openstack.identity.v3.project import Project
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.openstack import get_project
from tests.schemas.utils import random_lower_string


class CaseWithDesc:
    @parametrize(with_desc=[True, False])
    def case_with_desc(self, with_desc: bool) -> bool:
        return with_desc


@pytest.fixture
@parametrize_with_cases("with_desc", cases=CaseWithDesc)
def openstack_project(with_desc) -> Project:
    """Fixture with an Openstack project."""
    d = {"id": uuid4().hex, "name": random_lower_string()}
    if with_desc:
        d["description"] = random_lower_string()
    return Project(**d)


@patch("src.providers.openstack.Connection.identity")
@patch("src.providers.openstack.Connection")
def test_retrieve_project(
    mock_conn: Mock, mock_identity: Mock, openstack_project: Project
) -> None:
    """Successful retrieval of a project.

    Project retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    mock_identity.get_project.return_value = openstack_project
    mock_conn.identity = mock_identity
    type(mock_conn).current_project_id = PropertyMock(return_value=openstack_project.id)
    item = get_project(mock_conn)
    if openstack_project.description:
        assert item.description == openstack_project.description
    else:
        assert item.description == ""
    assert item.uuid == openstack_project.id
    assert item.name == openstack_project.name
