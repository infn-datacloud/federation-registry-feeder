from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from openstack.compute.v2.flavor import Flavor
from openstack.exceptions import ForbiddenException

from src.providers.openstack import get_flavors


@patch("src.providers.openstack.Connection.compute.get_flavor_access")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_flavors(
    mock_conn: Mock,
    mock_compute: Mock,
    mock_flavor_access: Mock,
    openstack_flavor: Flavor,
) -> None:
    """Successful retrieval of a flavors.

    Retrieve only active flavors.

    Flavors retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    flavors = list(filter(lambda x: not x.is_disabled, [openstack_flavor]))
    project_id = uuid4().hex
    mock_flavor_access.return_value = [{"tenant_id": project_id}]
    mock_compute.flavors.return_value = flavors
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_flavors(mock_conn)

    assert len(data) == len(flavors)
    if len(data) > 0:
        item = data[0]
        if openstack_flavor.description:
            assert item.description == openstack_flavor.description
        else:
            assert item.description == ""
        assert item.uuid == openstack_flavor.id
        assert item.name == openstack_flavor.name
        assert item.disk == openstack_flavor.disk
        assert item.is_public == openstack_flavor.is_public
        assert item.ram == openstack_flavor.ram
        assert item.vcpus == openstack_flavor.vcpus
        assert item.swap == openstack_flavor.swap
        assert item.ephemeral == openstack_flavor.ephemeral
        assert item.gpus == openstack_flavor.extra_specs.get("gpu_number", 0)
        assert item.gpu_model == openstack_flavor.extra_specs.get("gpu_model")
        assert item.gpu_vendor == openstack_flavor.extra_specs.get("gpu_vendor")
        assert item.local_storage == openstack_flavor.extra_specs.get(
            "aggregate_instance_extra_specs:local_storage"
        )
        assert item.infiniband == openstack_flavor.extra_specs.get("infiniband", False)
        if item.is_public:
            assert len(item.projects) == 0
        else:
            assert len(item.projects) == 1


@patch("src.providers.openstack.Connection.compute.get_flavor_access")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_no_matching_project_id_when_retrieving_private_flavor(
    mock_conn: Mock,
    mock_compute: Mock,
    mock_flavor_access: Mock,
    openstack_flavor_private: Flavor,
) -> None:
    """
    Filter out private flavors not visible to the current project.
    """
    flavors = list(filter(lambda x: not x.is_disabled, [openstack_flavor_private]))
    project_id = uuid4().hex
    mock_flavor_access.return_value = [{"tenant_id": project_id}]
    mock_compute.flavors.return_value = flavors
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    data = get_flavors(mock_conn)
    assert len(data) == 0


@patch("src.providers.openstack.Connection.compute.get_flavor_access")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_catch_forbidden_exception_when_reading_flavor_projects(
    mock_conn: Mock,
    mock_compute: Mock,
    mock_flavor_access: Mock,
    openstack_flavor_private: Flavor,
) -> None:
    """
    Catch ForbiddenException and filter out private flavors if the openstack policy does
    not allow to read os-flavor-access.
    """
    flavors = list(filter(lambda x: not x.is_disabled, [openstack_flavor_private]))
    mock_flavor_access.side_effect = ForbiddenException()
    mock_compute.flavors.return_value = flavors
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    data = get_flavors(mock_conn)
    assert len(data) == 0
