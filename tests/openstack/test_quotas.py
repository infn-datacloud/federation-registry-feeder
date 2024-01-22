from dataclasses import dataclass
from random import randint
from typing import Any, Dict, Optional
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


@dataclass
class FakeBlockStorage:
    backup_gigabytes: int = 0
    backups: int = 0
    gigabytes: int = 0
    groups: int = 0
    per_volume_gigabytes: int = 0
    snapshots: int = 0
    volumes: int = 0

    def get_quota_set(self, project: Any) -> BlockStorageQuotaSet:
        return BlockStorageQuotaSet(
            backup_gigabytes=self.backup_gigabytes,
            backups=self.backups,
            gigabytes=self.gigabytes,
            groups=self.groups,
            per_volume_gigabytes=self.per_volume_gigabytes,
            snapshots=self.snapshots,
            volumes=self.volumes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


@dataclass
class FakeCompute:
    cores: int = 0
    fixed_ips: int = 0
    floating_ips: int = 0
    force: bool = False
    injected_file_content_bytes: int = 0
    injected_file_path_bytes: int = 0
    injected_files: int = 0
    instances: int = 0
    key_pairs: int = 0
    metadata_items: int = 0
    networks: int = 0
    ram: int = 0
    security_group_rules: int = 0
    security_groups: int = 0
    server_groups: int = 0
    server_group_members: int = 0

    def get_quota_set(self, project: Any) -> ComputeQuotaSet:
        return ComputeQuotaSet(
            cores=self.cores,
            fixed_ips=self.fixed_ips,
            floating_ips=self.floating_ips,
            injected_file_content_bytes=self.injected_file_content_bytes,
            injected_file_path_bytes=self.injected_file_path_bytes,
            injected_files=self.injected_files,
            instances=self.instances,
            key_pairs=self.key_pairs,
            metadata_items=self.metadata_items,
            networks=self.networks,
            ram=self.ram,
            security_group_rules=self.security_group_rules,
            security_groups=self.security_groups,
            server_groups=self.server_groups,
            server_group_members=self.server_group_members,
            force=self.force,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


@dataclass
class FakeNetwork:
    check_limit: bool = False
    floating_ips: int = 0
    health_monitors: int = 0
    listeners: int = 0
    load_balancers: int = 0
    l7_policies: int = 0
    networks: int = 0
    pools: int = 0
    ports: int = 0
    # project_id: int = 0
    rbac_policies: int = 0
    routers: int = 0
    subnets: int = 0
    subnet_pools: int = 0
    security_group_rules: int = 0
    security_groups: int = 0

    def get_quota(self, project: Any) -> NetworkQuota:
        return NetworkQuota(
            check_limit=self.check_limit,
            floating_ips=self.floating_ips,
            health_monitors=self.health_monitors,
            listeners=self.listeners,
            load_balancers=self.load_balancers,
            l7_policies=self.l7_policies,
            networks=self.networks,
            pools=self.pools,
            ports=self.ports,
            # project_id=self.project_id,
            rbac_policies=self.rbac_policies,
            routers=self.routers,
            subnets=self.subnets,
            subnet_pools=self.subnet_pools,
            security_group_rules=self.security_group_rules,
            security_groups=self.security_groups,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


@dataclass
class FakeConn:
    current_project_id: str
    block_storage: Optional[FakeBlockStorage] = None
    compute: Optional[FakeCompute] = None
    network: Optional[FakeNetwork] = None


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


def test_retrieve_block_storage_quotas(block_storage_quotas: Dict[str, int]) -> None:
    conn = FakeConn(
        current_project_id=uuid4().hex,
        block_storage=FakeBlockStorage(**block_storage_quotas),
    )
    data = get_block_storage_quotas(conn)
    assert data.type == QuotaType.BLOCK_STORAGE
    assert not data.per_user
    assert data.gigabytes == block_storage_quotas.get("gigabytes")
    assert data.per_volume_gigabytes == block_storage_quotas.get("per_volume_gigabytes")
    assert data.volumes == block_storage_quotas.get("volumes")


def test_retrieve_compute_quotas(compute_quotas: Dict[str, int]) -> None:
    conn = FakeConn(
        current_project_id=uuid4().hex,
        compute=FakeCompute(**compute_quotas),
    )
    data = get_compute_quotas(conn)
    assert data.type == QuotaType.COMPUTE
    assert not data.per_user
    assert data.cores == compute_quotas.get("cores")
    assert data.instances == compute_quotas.get("instances")
    assert data.ram == compute_quotas.get("ram")


def test_retrieve_network_quotas(network_quotas: Dict[str, int]) -> None:
    conn = FakeConn(
        current_project_id=uuid4().hex,
        network=FakeNetwork(**network_quotas),
    )
    data = get_network_quotas(conn)
    assert data.type == QuotaType.NETWORK
    assert not data.per_user
    assert data.ports == network_quotas.get("ports")
    assert data.networks == network_quotas.get("networks")
    assert data.public_ips == network_quotas.get("floating_ips")
    assert data.security_groups == network_quotas.get("security_groups")
    assert data.security_group_rules == network_quotas.get("security_group_rules")
