from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.quota.enum import QuotaType
from openstack.block_storage.v3.quota_set import QuotaSet as BlockStorageQuotaSet
from openstack.compute.v2.quota_set import QuotaSet as ComputeQuotaSet
from openstack.exceptions import ForbiddenException
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
    data_limit, data_usage = get_block_storage_quotas(mock_conn)
    assert data_limit.type == QuotaType.BLOCK_STORAGE.value
    assert data_usage.type == QuotaType.BLOCK_STORAGE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.gigabytes == openstack_block_storage_quotas.get("gigabytes")
    assert data_usage.gigabytes == openstack_block_storage_quotas.get("usage").get(
        "gigabytes"
    )
    assert data_limit.per_volume_gigabytes == openstack_block_storage_quotas.get(
        "per_volume_gigabytes"
    )
    assert data_usage.per_volume_gigabytes == openstack_block_storage_quotas.get(
        "usage"
    ).get("per_volume_gigabytes")
    assert data_limit.volumes == openstack_block_storage_quotas.get("volumes")
    assert data_usage.volumes == openstack_block_storage_quotas.get("usage").get(
        "volumes"
    )
    assert data_limit.project == project_id
    assert data_usage.project == project_id


@patch("src.providers.openstack.Connection.block_storage")
@patch("src.providers.openstack.Connection")
def test_catch_forbidden_when_reading_block_storage_quotas(
    mock_conn: Mock, mock_block_storage: Mock
) -> None:
    """Retrieve a block storage quota."""
    mock_block_storage.get_quota_set.side_effect = ForbiddenException()
    mock_conn.block_storage = mock_block_storage
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data_limit, data_usage = get_block_storage_quotas(mock_conn)
    assert data_limit.type == QuotaType.BLOCK_STORAGE.value
    assert data_usage.type == QuotaType.BLOCK_STORAGE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.gigabytes is None
    assert data_usage.gigabytes is None
    assert data_limit.per_volume_gigabytes is None
    assert data_usage.per_volume_gigabytes is None
    assert data_limit.volumes is None
    assert data_usage.volumes is None
    assert data_limit.project == project_id
    assert data_usage.project == project_id


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
    data_limit, data_usage = get_compute_quotas(mock_conn)
    assert data_limit.type == QuotaType.COMPUTE.value
    assert data_usage.type == QuotaType.COMPUTE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.cores == openstack_compute_quotas.get("cores")
    assert data_usage.cores == openstack_compute_quotas.get("usage").get("cores")
    assert data_limit.instances == openstack_compute_quotas.get("instances")
    assert data_usage.instances == openstack_compute_quotas.get("usage").get(
        "instances"
    )
    assert data_limit.ram == openstack_compute_quotas.get("ram")
    assert data_usage.ram == openstack_compute_quotas.get("usage").get("ram")
    assert data_limit.project == project_id
    assert data_usage.project == project_id


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
    data_limit, data_usage = get_network_quotas(mock_conn)
    assert data_limit.type == QuotaType.NETWORK.value
    assert data_usage.type == QuotaType.NETWORK.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.ports == openstack_network_quotas.get("ports").get("limit")
    assert data_usage.ports == openstack_network_quotas.get("ports").get("used")
    assert data_limit.networks == openstack_network_quotas.get("networks").get("limit")
    assert data_usage.networks == openstack_network_quotas.get("networks").get("used")
    assert data_limit.public_ips == openstack_network_quotas.get("floating_ips").get(
        "limit"
    )
    assert data_usage.public_ips == openstack_network_quotas.get("floating_ips").get(
        "used"
    )
    assert data_limit.security_groups == openstack_network_quotas.get(
        "security_groups"
    ).get("limit")
    assert data_usage.security_groups == openstack_network_quotas.get(
        "security_groups"
    ).get("used")
    assert data_limit.security_group_rules == openstack_network_quotas.get(
        "security_group_rules"
    ).get("limit")
    assert data_usage.security_group_rules == openstack_network_quotas.get(
        "security_group_rules"
    ).get("used")
    assert data_limit.project == project_id
    assert data_usage.project == project_id
