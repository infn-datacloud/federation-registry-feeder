from unittest.mock import PropertyMock, patch
from uuid import uuid4

import pytest
from openstack.identity.v3.project import Project

from src.providers.openstack import get_project
from tests.schemas.utils import random_lower_string


@pytest.fixture
def project() -> Project:
    return Project(
        id=uuid4().hex, name=random_lower_string(), description=random_lower_string()
    )


@patch("src.providers.openstack.Connection.identity")
@patch("src.providers.openstack.Connection")
def test_retrieve_project(mock_conn, mock_identity, project: Project) -> None:
    mock_identity.get_project.return_value = project
    mock_conn.identity = mock_identity
    type(mock_conn).current_project_id = PropertyMock(return_value=project.id)
    item = get_project(mock_conn)
    assert item.description == project.description
    assert item.uuid == project.id
    assert item.name == project.name
