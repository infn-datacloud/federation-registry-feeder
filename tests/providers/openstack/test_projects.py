from logging import getLogger
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

import pytest
from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ProjectCreate,
)
from openstack.identity.v3.project import Project as OpenstackProject
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Openstack, Project
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
)


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


@patch("src.providers.openstack.Connection.identity")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_project(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_identity: Mock,
    openstack_project: OpenstackProject,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """Successful retrieval of a project.

    Project retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    project_conf = Project(**project_dict())
    project_conf.id = openstack_project.id
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    mock_identity.get_project.return_value = openstack_project
    mock_conn.identity = mock_identity
    type(mock_conn).current_project_id = PropertyMock(return_value=openstack_project.id)
    item.conn = mock_conn

    item = item.get_project()
    assert isinstance(item, ProjectCreate)
    if openstack_project.description:
        assert item.description == openstack_project.description
    else:
        assert item.description == ""
    assert item.uuid == openstack_project.id
    assert item.name == openstack_project.name

    mock_identity.get_project.assert_called_once()
