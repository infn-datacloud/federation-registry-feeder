import copy

from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    RegionCreateExtended,
)

from src.utils import get_updated_region
from tests.fed_reg.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_network_service_name,
    random_object_store_service_name,
)
from tests.utils import random_url


def test_add_new_region(
    region_create: RegionCreateExtended,
) -> None:
    item = get_updated_region(current_region=None, new_region=region_create)
    assert item == region_create


def test_new_region_matches_old_ons(
    region_create: RegionCreateExtended,
) -> None:
    item = get_updated_region(current_region=region_create, new_region=region_create)
    assert item == region_create


def test_new_region_has_new_services(region_create: RegionCreateExtended) -> None:
    current_region = copy.deepcopy(region_create)
    current_region.block_storage_services[0] = BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=random_block_storage_service_name()
    )
    current_region.compute_services[0] = ComputeServiceCreateExtended(
        endpoint=random_url(), name=random_compute_service_name()
    )
    current_region.identity_services[0] = IdentityServiceCreate(
        endpoint=random_url(), name=random_identity_service_name()
    )
    current_region.network_services[0] = NetworkServiceCreateExtended(
        endpoint=random_url(), name=random_network_service_name()
    )
    current_region.object_store_services[0] = ObjectStoreServiceCreateExtended(
        endpoint=random_url(), name=random_object_store_service_name()
    )
    item = get_updated_region(current_region=current_region, new_region=region_create)
    assert len(item.block_storage_services) == 2
    assert len(item.compute_services) == 2
    assert len(item.identity_services) == 2
    assert len(item.network_services) == 2
    assert len(item.object_store_services) == 2
