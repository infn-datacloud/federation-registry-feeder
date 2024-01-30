from typing import Union

import pytest
from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    RegionCreateExtended,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.core import update_regions
from tests.schemas.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_lower_string,
    random_network_service_name,
    random_url,
)


@parametrize(n=[1, 2])
def case_tot_regions(n: int) -> int:
    return n


@pytest.fixture
def block_storage_service() -> BlockStorageServiceCreateExtended:
    return BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=random_block_storage_service_name()
    )


@pytest.fixture
def compute_service() -> ComputeServiceCreateExtended:
    return ComputeServiceCreateExtended(
        endpoint=random_url(), name=random_compute_service_name()
    )


@pytest.fixture
def identity_service() -> IdentityServiceCreate:
    return IdentityServiceCreate(
        endpoint=random_url(), name=random_identity_service_name()
    )


@pytest.fixture
def network_service() -> NetworkServiceCreateExtended:
    return NetworkServiceCreateExtended(
        endpoint=random_url(), name=random_network_service_name()
    )


@pytest.fixture
@parametrize(
    s=[
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    ]
)
def service(
    s: Union[
        BlockStorageServiceCreateExtended,
        ComputeServiceCreateExtended,
        IdentityServiceCreate,
        NetworkServiceCreateExtended,
    ],
) -> Union[
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
]:
    return s


@parametrize_with_cases("tot_regions", cases=".")
def test_update_region(
    service: Union[
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
        if isinstance(service, BlockStorageServiceCreateExtended):
            region.block_storage_services.append(service)
        elif isinstance(service, ComputeServiceCreateExtended):
            region.compute_services.append(service)
        elif isinstance(service, IdentityServiceCreate):
            region.identity_services.append(service)
        elif isinstance(service, NetworkServiceCreateExtended):
            region.network_services.append(service)
        regions.append(region)
    update_regions(new_regions=regions, include_projects=[])
