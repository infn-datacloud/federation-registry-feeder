from typing import Union

from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    RegionCreateExtended,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.core import update_regions
from tests.schemas.utils import random_lower_string


@parametrize(n=[1, 2])
def case_tot_regions(n: int) -> int:
    return n


@parametrize_with_cases("tot_regions", cases=".")
def test_update_region(
    service_create: Union[
        BlockStorageServiceCreateExtended,
        ComputeServiceCreateExtended,
        IdentityServiceCreate,
        NetworkServiceCreateExtended,
    ],
    tot_regions: int,
) -> None:
    regions = []
    name = random_lower_string()
    for _ in range(tot_regions):
        region = RegionCreateExtended(name=name)
        if isinstance(service_create, BlockStorageServiceCreateExtended):
            region.block_storage_services.append(service_create)
        elif isinstance(service_create, ComputeServiceCreateExtended):
            region.compute_services.append(service_create)
        elif isinstance(service_create, IdentityServiceCreate):
            region.identity_services.append(service_create)
        elif isinstance(service_create, NetworkServiceCreateExtended):
            region.network_services.append(service_create)
        regions.append(region)
    update_regions(new_regions=regions, include_projects=[])
