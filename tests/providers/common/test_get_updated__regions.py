import copy

from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    RegionCreateExtended,
)
from pytest_cases import parametrize_with_cases

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


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_add_new_region(
    provider_thread_item: ProviderThread,
    region_create: RegionCreateExtended,
) -> None:
    item = provider_thread_item.get_updated_region(
        current_region=None, new_region=region_create
    )
    assert item == region_create


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_new_region_matches_old_ons(
    provider_thread_item: ProviderThread,
    region_create: RegionCreateExtended,
) -> None:
    item = provider_thread_item.get_updated_region(
        current_region=region_create, new_region=region_create
    )
    assert item == region_create


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_new_region_has_new_services(
    provider_thread_item: ProviderThread, region_create: RegionCreateExtended
) -> None:
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
    item = provider_thread_item.get_updated_region(
        current_region=current_region, new_region=region_create
    )
    assert len(item.block_storage_services) == 2
    assert len(item.compute_services) == 2
    assert len(item.identity_services) == 2
    assert len(item.network_services) == 2
    assert len(item.object_store_services) == 2
