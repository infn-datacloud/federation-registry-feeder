from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

import pytest
from fed_reg.provider.schemas_extended import (
    ProjectCreate,
)
from keystoneauth1.exceptions.connection import ConnectFailure
from openstack.identity.v3.project import Project as OpenstackProject
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.openstack import OpenstackData
from tests.utils import random_lower_string


class CaseWithDesc:
    @parametrize(with_desc=(True, False))
    def case_with_desc(self, with_desc: bool) -> bool:
        return with_desc


@pytest.fixture
@parametrize_with_cases("with_desc", cases=CaseWithDesc)
def openstack_project(with_desc: bool) -> OpenstackProject:
    """Fixture with an Openstack project."""
    d = {"id": uuid4().hex, "name": random_lower_string()}
    if with_desc:
        d["description"] = random_lower_string()
    return OpenstackProject(**d)


@patch("src.providers.openstack.Connection")
def test_retrieve_project(
    mock_conn: Mock,
    openstack_project: OpenstackProject,
    openstack_item: OpenstackData,
) -> None:
    """Successful retrieval of a project.

    Project retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    openstack_item.project_conf.id = openstack_project.id
    mock_conn.identity.get_project.return_value = openstack_project
    type(mock_conn).current_project_id = PropertyMock(return_value=openstack_project.id)
    openstack_item.conn = mock_conn

    item = openstack_item.get_project()
    assert isinstance(item, ProjectCreate)
    if openstack_project.description:
        assert item.description == openstack_project.description
    else:
        assert item.description == ""
    assert item.uuid == openstack_project.id
    assert item.name == openstack_project.name

    mock_conn.identity.get_project.assert_called_once()


@patch("src.providers.openstack.Connection")
def test_name_resolution_error(
    mock_conn: Mock,
    openstack_project: OpenstackProject,
    openstack_item: OpenstackData,
) -> None:
    """Successful retrieval of a project.

    Project retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    openstack_item.project_conf.id = openstack_project.id
    mock_conn.identity.get_project.side_effect = ConnectFailure()
    type(mock_conn).current_project_id = PropertyMock(return_value=openstack_project.id)
    openstack_item.conn = mock_conn

    with pytest.raises(ConnectFailure):
        openstack_item.get_project()
