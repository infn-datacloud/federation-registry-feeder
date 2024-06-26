from typing import Literal, Tuple, Union

from fed_reg.quota.enum import QuotaType
from fed_reg.quota.schemas import (
    BlockStorageQuotaBase,
    ComputeQuotaBase,
    NetworkQuotaBase,
)
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits


class CaseQuotaType:
    def case_block_storage_quota(
        self, block_storage_quota: BlockStorageQuotaBase
    ) -> Tuple[Literal[QuotaType.BLOCK_STORAGE], BlockStorageQuotaBase]:
        return QuotaType.BLOCK_STORAGE, block_storage_quota

    def case_compute_quota(
        self, compute_quota: ComputeQuotaBase
    ) -> Tuple[Literal[QuotaType.COMPUTE], ComputeQuotaBase]:
        return QuotaType.COMPUTE, compute_quota

    def case_network_quota(
        self, network_quota: NetworkQuotaBase
    ) -> Tuple[Literal[QuotaType.NETWORK], NetworkQuotaBase]:
        return QuotaType.NETWORK, network_quota


@parametrize_with_cases("key, value", cases=CaseQuotaType)
def test_limit_schema(
    key: str, value: Union[BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase]
) -> None:
    """Create a Limits schema with or without quotas."""
    if key == QuotaType.BLOCK_STORAGE:
        item = Limits(block_storage=value)
        assert item.block_storage.per_user
        assert item.block_storage.type == value.type
        assert item.block_storage.gigabytes == value.gigabytes
        assert item.block_storage.per_volume_gigabytes == value.per_volume_gigabytes
        assert item.block_storage.volumes == value.volumes
    elif key == QuotaType.COMPUTE:
        item = Limits(compute=value)
        assert item.compute.per_user
        assert item.compute.type == value.type
        assert item.compute.cores == value.cores
        assert item.compute.instances == value.instances
        assert item.compute.ram == value.ram
    elif key == QuotaType.NETWORK:
        item = Limits(network=value)
        assert item.network.per_user
        assert item.network.type == value.type
        assert item.network.public_ips == value.public_ips
        assert item.network.networks == value.networks
        assert item.network.ports == value.ports
        assert item.network.security_groups == value.security_groups
        assert item.network.security_group_rules == value.security_group_rules
