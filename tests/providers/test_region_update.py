from typing import Tuple, Union
from uuid import uuid4

from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityServiceCreate,
    ImageCreateExtended,
    NetworkServiceCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.core import update_regions
from tests.schemas.utils import random_lower_string


class CaseTotRegions:
    @parametrize(n=[0, 1, 2])
    def case_tot_regions(self, n: int) -> int:
        return n


class CaseResources:
    def case_single_project(
        self, project_create: ProjectCreate
    ) -> Tuple[FlavorCreateExtended, ImageCreateExtended]:
        return (
            FlavorCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=[project_create.uuid],
            ),
            ImageCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=[project_create.uuid],
            ),
        )

    def case_multiple_projects(
        self, project_create: ProjectCreate
    ) -> Tuple[FlavorCreateExtended, ImageCreateExtended]:
        return (
            FlavorCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=[project_create.uuid, uuid4().hex],
            ),
            ImageCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=[project_create.uuid, uuid4().hex],
            ),
        )


@parametrize_with_cases("tot_regions", cases=CaseTotRegions)
def test_update_region(
    service_create: Union[
        BlockStorageServiceCreateExtended,
        ComputeServiceCreateExtended,
        IdentityServiceCreate,
        NetworkServiceCreateExtended,
    ],
    tot_regions: int,
) -> None:
    """Test how the regions are updated.

    Change the number of regions and the type of service.
    """
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
    new_regions = update_regions(new_regions=regions, include_projects=[])

    assert len(new_regions) == min(tot_regions, 1)
    if len(new_regions) == 1:
        assert new_regions[0].name == name
        assert len(new_regions[0].block_storage_services) == min(
            len(region.block_storage_services), 1
        )
        assert len(new_regions[0].compute_services) == min(
            len(region.compute_services), 1
        )
        assert len(new_regions[0].identity_services) == min(
            len(region.identity_services), 1
        )
        assert len(new_regions[0].network_services) == min(
            len(region.network_services), 1
        )


@parametrize_with_cases("resources", cases=CaseResources)
def test_update_region_forward_include_projects(
    compute_service_create: ComputeServiceCreateExtended,
    project_create: ProjectCreate,
    resources: Tuple[FlavorCreateExtended, ImageCreateExtended],
) -> None:
    """Test how the regions are updated.

    Change the number of regions and the type of service.
    """
    flavor, image = resources
    compute_service_create.flavors = [flavor]
    compute_service_create.images = [image]
    region = RegionCreateExtended(
        name=random_lower_string(), compute_services=[compute_service_create]
    )
    new_regions = update_regions(
        new_regions=[region], include_projects=[project_create.uuid]
    )

    assert len(new_regions) == 1
    new_region = new_regions[0]
    assert len(new_region.compute_services) == 1
    compute_service = new_region.compute_services[0]
    assert len(compute_service.flavors) == 1
    flavor = compute_service.flavors[0]
    assert len(flavor.projects) == 1
    assert len(compute_service.images) == 1
    image = compute_service.images[0]
    assert len(image.projects) == 1
