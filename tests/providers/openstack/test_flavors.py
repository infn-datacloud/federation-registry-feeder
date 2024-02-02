from typing import Dict, List
from unittest.mock import Mock, patch
from uuid import uuid4

from openstack.compute.v2.flavor import Flavor

from src.providers.openstack import get_flavors


def get_allowed_project_ids(*args, **kwargs) -> List[Dict[str, str]]:
    return [{"tenant_id": uuid4().hex}]


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_flavors(
    mock_conn: Mock, mock_compute: Mock, openstack_flavor: Flavor
) -> None:
    """Successful retrieval of a flavors.

    Retrieve only active flavors.

    Flavors retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    flavors = list(filter(lambda x: not x.is_disabled, [openstack_flavor]))
    mock_compute.flavors.return_value = flavors
    mock_compute.get_flavor_access.side_effect = get_allowed_project_ids
    mock_conn.compute = mock_compute
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
            assert len(item.projects) == len(get_allowed_project_ids())
