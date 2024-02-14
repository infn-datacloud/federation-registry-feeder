from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.quota.enum import QuotaType
from openstack.block_storage.v3.quota_set import QuotaSet as BlockStorageQuotaSet
from openstack.compute.v2.quota_set import QuotaSet as ComputeQuotaSet
from openstack.network.v2.quota import Quota as NetworkQuota

from src.providers.openstack import (
    get_block_storage_quotas,
    get_compute_quotas,
    get_network_quotas,
)


@patch("src.providers.openstack.Connection.block_storage")
@patch("src.providers.openstack.Connection")
def test_retrieve_block_storage_quotas(
    mock_conn: Mock,
    mock_block_storage: Mock,
    openstack_block_storage_quotas: BlockStorageQuotaSet,
) -> None:
    """Retrieve a block storage quota."""
    mock_block_storage.get_quota_set.return_value = openstack_block_storage_quotas
    mock_conn.block_storage = mock_block_storage
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_block_storage_quotas(mock_conn)
    assert data.type == QuotaType.BLOCK_STORAGE.value
    assert not data.per_user
    assert data.gigabytes == openstack_block_storage_quotas.get("gigabytes")
    assert data.per_volume_gigabytes == openstack_block_storage_quotas.get(
        "per_volume_gigabytes"
    )
    assert data.volumes == openstack_block_storage_quotas.get("volumes")
    assert data.project == project_id


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_quotas(
    mock_conn: Mock, mock_compute: Mock, openstack_compute_quotas: ComputeQuotaSet
) -> None:
    """Retrieve a compute quota."""
    mock_compute.get_quota_set.return_value = openstack_compute_quotas
    mock_conn.compute = mock_compute
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_compute_quotas(mock_conn)
    assert data.type == QuotaType.COMPUTE.value
    assert not data.per_user
    assert data.cores == openstack_compute_quotas.get("cores")
    assert data.instances == openstack_compute_quotas.get("instances")
    assert data.ram == openstack_compute_quotas.get("ram")
    assert data.project == project_id


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_quotas(
    mock_conn: Mock, mock_network: Mock, openstack_network_quotas: NetworkQuota
) -> None:
    """Retrieve a network quota."""
    mock_network.get_quota.return_value = openstack_network_quotas
    mock_conn.network = mock_network
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_network_quotas(mock_conn)
    assert data.type == QuotaType.NETWORK.value
    assert not data.per_user
    assert data.ports == openstack_network_quotas.get("ports")
    assert data.networks == openstack_network_quotas.get("networks")
    assert data.public_ips == openstack_network_quotas.get("floating_ips")
    assert data.security_groups == openstack_network_quotas.get("security_groups")
    assert data.security_group_rules == openstack_network_quotas.get(
        "security_group_rules"
    )
    assert data.project == project_id
