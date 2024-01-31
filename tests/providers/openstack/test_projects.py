from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

import pytest
from keystoneauth1.exceptions.http import Unauthorized
from openstack.identity.v3.project import Project
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.openstack import get_project
from tests.schemas.utils import random_lower_string


@parametrize(with_desc=[True, False])
def case_with_desc(with_desc: bool) -> bool:
    return with_desc


@pytest.fixture
@parametrize_with_cases("with_desc", cases=".")
def project(with_desc) -> Project:
    d = {"id": uuid4().hex, "name": random_lower_string()}
    if with_desc:
        d["description"] = random_lower_string()
    return Project(**d)


@patch("src.providers.openstack.Connection.identity")
@patch("src.providers.openstack.Connection")
def test_retrieve_project(
    mock_conn: Mock, mock_identity: Mock, project: Project
) -> None:
    mock_identity.get_project.return_value = project
    mock_conn.identity = mock_identity
    type(mock_conn).current_project_id = PropertyMock(return_value=project.id)
    item = get_project(mock_conn)
    assert item.description == (project.description if project.description else "")
    assert item.uuid == project.id
    assert item.name == project.name


@patch("src.providers.openstack.Connection.identity")
@patch("src.providers.openstack.Connection")
def test_fail_retrieve_project(
    mock_conn: Mock, mock_identity: Mock, project: Project
) -> None:
    mock_identity.get_project.side_effect = Unauthorized()
    mock_conn.identity = mock_identity
    type(mock_conn).current_project_id = PropertyMock(return_value=project.id)
    with pytest.raises(Unauthorized):
        get_project(mock_conn)
