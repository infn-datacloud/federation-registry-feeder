from random import randint
from typing import Dict
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

import pytest
from app.quota.enum import QuotaType
from openstack.block_storage.v3.quota_set import QuotaSet as BlockStorageQuotaSet
from openstack.compute.v2.quota_set import QuotaSet as ComputeQuotaSet
from openstack.network.v2.quota import Quota as NetworkQuota

from src.providers.openstack import (
    get_block_storage_quotas,
    get_compute_quotas,
    get_network_quotas,
)


@pytest.fixture
def block_storage_quotas() -> Dict[str, int]:
    return {
        "backup_gigabytes": randint(0, 100),
        "backups": randint(0, 100),
        "gigabytes": randint(0, 100),
        "groups": randint(0, 100),
        "per_volume_gigabytes": randint(0, 100),
        "snapshots": randint(0, 100),
        "volumes": randint(0, 100),
    }


@pytest.fixture
def compute_quotas() -> Dict[str, int]:
    return {
        "cores": randint(0, 100),
        "fixed_ips": randint(0, 100),
        "floating_ips": randint(0, 100),
        "injected_file_content_bytes": randint(0, 100),
        "injected_file_path_bytes": randint(0, 100),
        "injected_files": randint(0, 100),
        "instances": randint(0, 100),
        "key_pairs": randint(0, 100),
        "metadata_items": randint(0, 100),
        "networks": randint(0, 100),
        "ram": randint(0, 100),
        "security_group_rules": randint(0, 100),
        "security_groups": randint(0, 100),
        "server_groups": randint(0, 100),
        "server_group_members": randint(0, 100),
        "force": False,
    }


@pytest.fixture
def network_quotas() -> Dict[str, int]:
    return {
        "check_limit": False,
        "floating_ips": randint(0, 100),
        "health_monitors": randint(0, 100),
        "listeners": randint(0, 100),
        "load_balancers": randint(0, 100),
        "l7_policies": randint(0, 100),
        "networks": randint(0, 100),
        "pools": randint(0, 100),
        "ports": randint(0, 100),
        # "project_id": ?,
        "rbac_policies": randint(0, 100),
        "routers": randint(0, 100),
        "subnets": randint(0, 100),
        "subnet_pools": randint(0, 100),
        "security_group_rules": randint(0, 100),
        "security_groups": randint(0, 100),
    }


@patch("src.providers.openstack.Connection.block_storage")
@patch("src.providers.openstack.Connection")
def test_retrieve_block_storage_quotas(
    mock_conn: Mock, mock_block_storage: Mock, block_storage_quotas: Dict[str, int]
) -> None:
    mock_block_storage.get_quota_set.return_value = BlockStorageQuotaSet(
        **block_storage_quotas
    )
    mock_conn.block_storage = mock_block_storage
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_block_storage_quotas(mock_conn)
    assert data.type == QuotaType.BLOCK_STORAGE.value
    assert not data.per_user
    assert data.gigabytes == block_storage_quotas.get("gigabytes")
    assert data.per_volume_gigabytes == block_storage_quotas.get("per_volume_gigabytes")
    assert data.volumes == block_storage_quotas.get("volumes")
    assert data.project == project_id


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_quotas(
    mock_conn: Mock, mock_compute: Mock, compute_quotas: Dict[str, int]
) -> None:
    mock_compute.get_quota_set.return_value = ComputeQuotaSet(**compute_quotas)
    mock_conn.compute = mock_compute
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_compute_quotas(mock_conn)
    assert data.type == QuotaType.COMPUTE.value
    assert not data.per_user
    assert data.cores == compute_quotas.get("cores")
    assert data.instances == compute_quotas.get("instances")
    assert data.ram == compute_quotas.get("ram")
    assert data.project == project_id


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_quotas(
    mock_conn: Mock, mock_network: Mock, network_quotas: Dict[str, int]
) -> None:
    mock_network.get_quota.return_value = NetworkQuota(**network_quotas)
    mock_conn.network = mock_network
    project_id = uuid4().hex
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    data = get_network_quotas(mock_conn)
    assert data.type == QuotaType.NETWORK.value
    assert not data.per_user
    assert data.ports == network_quotas.get("ports")
    assert data.networks == network_quotas.get("networks")
    assert data.public_ips == network_quotas.get("floating_ips")
    assert data.security_groups == network_quotas.get("security_groups")
    assert data.security_group_rules == network_quotas.get("security_group_rules")
    assert data.project == project_id
