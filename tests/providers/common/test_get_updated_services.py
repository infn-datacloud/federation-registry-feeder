import copy
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
)
from pytest_cases import case, parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.core import ProviderThread
from tests.fed_reg.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_network_service_name,
    random_object_store_service_name,
)
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string, random_url


class CaseProviderThread:
    def case_openstack(self) -> ProviderThread:
        provider = Openstack(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])

    def case_k8s(self) -> ProviderThread:
        provider = Kubernetes(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])


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


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("services", cases=CaseService)
def test_add_new_service(
    provider_thread_item: ProviderThread,
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = services[1:]
    update_services = provider_thread_item.get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 2


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("services", cases=CaseService, has_tag="quota")
def test_update_existing_service_quotas(
    provider_thread_item: ProviderThread,
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    update_services = provider_thread_item.get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].quotas) == 2


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("services", cases=CaseService, has_tag="flavor")
def test_update_existing_service_flavors(
    provider_thread_item: ProviderThread,
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    new_srv[0].flavors[0] = services[1].flavors[0]
    update_services = provider_thread_item.get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].flavors) == 2


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("services", cases=CaseService, has_tag="image")
def test_update_existing_service_images(
    provider_thread_item: ProviderThread,
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    new_srv[0].images[0] = services[1].images[0]
    update_services = provider_thread_item.get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].images) == 2


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("services", cases=CaseService, has_tag="network")
def test_update_existing_service_networks(
    provider_thread_item: ProviderThread,
    services: list[BlockStorageServiceCreateExtended]
    | list[ComputeServiceCreateExtended]
    | list[NetworkServiceCreateExtended]
    | list[ObjectStoreServiceCreateExtended],
) -> None:
    curr_srv = services[:1]
    new_srv = copy.deepcopy(services[:1])
    new_srv[0].quotas[0].project = services[1].quotas[0].project
    new_srv[0].networks[0] = services[1].networks[0]
    update_services = provider_thread_item.get_updated_services(
        current_services=curr_srv, new_services=new_srv
    )
    assert len(update_services) == 1
    assert len(update_services[0].networks) == 2
