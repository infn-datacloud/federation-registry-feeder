from random import randint

import pytest
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Limits


@pytest.fixture
def block_storage_quota() -> BlockStorageQuotaBase:
    """Fixture with an SLA without projects."""
    return BlockStorageQuotaBase(
        gigabytes=randint(0, 100),
        per_volume_gigabytes=randint(0, 100),
        volumes=randint(1, 100),
    )


@pytest.fixture
def compute_quota() -> ComputeQuotaBase:
    """Fixture with an SLA without projects."""
    return ComputeQuotaBase(
        cores=randint(0, 100),
        instances=randint(0, 100),
        ram=randint(1, 100),
    )


@pytest.fixture
def network_quota() -> NetworkQuotaBase:
    """Fixture with an SLA without projects."""
    return NetworkQuotaBase(
        public_ips=randint(0, 100),
        networks=randint(0, 100),
        ports=randint(1, 100),
        security_groups=randint(1, 100),
        security_group_rules=randint(1, 100),
    )


@parametrize(type=["block_storage", "compute", "network"])
def case_quota_type(type: str) -> str:
    return type


@parametrize_with_cases("qtype", cases=".")
def test_limit_schema(
    qtype: str,
    block_storage_quota: BlockStorageQuotaBase,
    compute_quota: ComputeQuotaBase,
    network_quota: NetworkQuotaBase,
) -> None:
    """Create a Limits schema with or without quotas."""
    if qtype == "block_storage":
        item = Limits(block_storage=block_storage_quota)
        quota: BlockStorageQuotaBase = item.__getattribute__(qtype)
        assert quota.type == block_storage_quota.type
        assert quota.gigabytes == block_storage_quota.gigabytes
        assert quota.per_volume_gigabytes == block_storage_quota.per_volume_gigabytes
        assert quota.volumes == block_storage_quota.volumes
    elif qtype == "compute":
        item = Limits(compute=compute_quota)
        quota: ComputeQuotaBase = item.__getattribute__(qtype)
        assert quota.type == compute_quota.type
        assert quota.cores == compute_quota.cores
        assert quota.instances == compute_quota.instances
        assert quota.ram == compute_quota.ram
    elif qtype == "network":
        item = Limits(network=network_quota)
        quota: NetworkQuotaBase = item.__getattribute__(qtype)
        assert quota.type == network_quota.type
        assert quota.public_ips == network_quota.public_ips
        assert quota.networks == network_quota.networks
        assert quota.ports == network_quota.ports
        assert quota.security_groups == network_quota.security_groups
        assert quota.security_group_rules == network_quota.security_group_rules
    assert quota.per_user
