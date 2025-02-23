import copy
from uuid import uuid4

from fedreg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
)
from pytest_cases import case, parametrize_with_cases

from src.utils import get_updated_services
from tests.fed_reg.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_network_service_name,
    random_object_store_service_name,
)
from tests.utils import random_lower_string, random_url


class CaseService:
    @case(tags="quota")
    def case_block_storage(self) -> list[BlockStorageServiceCreateExtended]:
        return [
            BlockStorageServiceCreateExtended(
                endpoint=random_url(),
                name=random_block_storage_service_name(),
                quotas=[{"project": uuid4()}],
            ),
            BlockStorageServiceCreateExtended(
                endpoint=random_url(),
                name=random_block_storage_service_name(),
                quotas=[{"project": uuid4()}],
            ),
        ]

    @case(tags=("quota", "flavor", "image"))
    def case_compute(self) -> list[ComputeServiceCreateExtended]:
        return [
            ComputeServiceCreateExtended(
                endpoint=random_url(),
                name=random_compute_service_name(),
                quotas=[{"project": uuid4()}],
                flavors=[{"name": random_lower_string(), "uuid": uuid4()}],
                images=[{"name": random_lower_string(), "uuid": uuid4()}],
            ),
            ComputeServiceCreateExtended(
                endpoint=random_url(),
                name=random_compute_service_name(),
                quotas=[{"project": uuid4()}],
                flavors=[{"name": random_lower_string(), "uuid": uuid4()}],
                images=[{"name": random_lower_string(), "uuid": uuid4()}],
            ),
        ]

    def case_identity(self) -> list[IdentityServiceCreate]:
        return [
            IdentityServiceCreate(
                endpoint=random_url(), name=random_identity_service_name()
            ),
            IdentityServiceCreate(
                endpoint=random_url(), name=random_identity_service_name()
            ),
        ]

    @case(tags=("quota", "network"))
    def case_networks(self) -> list[NetworkServiceCreateExtended]:
        return [
            NetworkServiceCreateExtended(
                endpoint=random_url(),
                name=random_network_service_name(),
                quotas=[{"project": uuid4()}],
                networks=[{"name": random_lower_string(), "uuid": uuid4()}],
            ),
            NetworkServiceCreateExtended(
                endpoint=random_url(),
                name=random_network_service_name(),
                quotas=[{"project": uuid4()}],
                networks=[{"name": random_lower_string(), "uuid": uuid4()}],
            ),
        ]

    @case(tags="quota")
    def case_object_store(self) -> list[ObjectStoreServiceCreateExtended]:
        return [
            ObjectStoreServiceCreateExtended(
                endpoint=random_url(),
                name=random_object_store_service_name(),
                quotas=[{"project": uuid4()}],
            ),
            ObjectStoreServiceCreateExtended(
                endpoint=random_url(),
                name=random_object_store_service_name(),
                quotas=[{"project": uuid4()}],
            ),
        ]


@parametrize_with_cases("services", cases=CaseService)
def test_add_new_service(
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = services[1:]
    update_services = get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 2


@parametrize_with_cases("services", cases=CaseService, has_tag="quota")
def test_update_existing_service_quotas(
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    update_services = get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].quotas) == 2


@parametrize_with_cases("services", cases=CaseService, has_tag="flavor")
def test_update_existing_service_flavors(
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    new_srv[0].flavors[0] = services[1].flavors[0]
    update_services = get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].flavors) == 2


@parametrize_with_cases("services", cases=CaseService, has_tag="image")
def test_update_existing_service_images(
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    new_srv[0].images[0] = services[1].images[0]
    update_services = get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].images) == 2


@parametrize_with_cases("services", cases=CaseService, has_tag="network")
def test_update_existing_service_networks(
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    new_srv[0].networks[0] = services[1].networks[0]
    update_services = get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].networks) == 2
