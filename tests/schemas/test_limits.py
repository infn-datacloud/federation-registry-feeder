from fedreg.quota.enum import QuotaType
from fedreg.quota.schemas import (
    BlockStorageQuotaBase,
    ComputeQuotaBase,
    NetworkQuotaBase,
    ObjectStoreQuotaBase,
)
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits


class CaseQuota:
    def case_block_storage_quota(self) -> BlockStorageQuotaBase:
        return BlockStorageQuotaBase()

    def case_compute_quota(self) -> ComputeQuotaBase:
        return ComputeQuotaBase()

    def case_network_quota(self) -> NetworkQuotaBase:
        return NetworkQuotaBase()

    def case_object_store_quota(self) -> ObjectStoreQuotaBase:
        return ObjectStoreQuotaBase()


@parametrize_with_cases("value", cases=CaseQuota)
def test_limit_schema(
    value: BlockStorageQuotaBase
    | ComputeQuotaBase
    | NetworkQuotaBase
    | ObjectStoreQuotaBase,
) -> None:
    """Create a Limits schema with or without quotas."""
    if value.type == QuotaType.BLOCK_STORAGE:
        item = Limits(block_storage=value)
        assert item.block_storage is not None
        assert isinstance(item.block_storage, BlockStorageQuotaBase)
        assert item.block_storage.per_user
    elif value.type == QuotaType.COMPUTE:
        item = Limits(compute=value)
        assert item.compute is not None
        assert isinstance(item.compute, ComputeQuotaBase)
        assert item.compute.per_user
    elif value.type == QuotaType.NETWORK:
        item = Limits(network=value)
        assert item.network is not None
        assert isinstance(item.network, NetworkQuotaBase)
        assert item.network.per_user
    elif value.type == QuotaType.OBJECT_STORE:
        item = Limits(object_store=value)
        assert item.object_store is not None
        assert isinstance(item.object_store, ObjectStoreQuotaBase)
        assert item.object_store.per_user
