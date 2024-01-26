import copy
from random import randint
from typing import Tuple
from uuid import uuid4

from app.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    BlockStorageServiceCreateExtended,
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityServiceCreate,
    ImageCreateExtended,
    NetworkCreateExtended,
    NetworkQuotaCreateExtended,
    NetworkServiceCreateExtended,
)
from pytest_cases import case, parametrize, parametrize_with_cases

from src.providers.core import (
    update_region_block_storage_services,
    update_region_compute_services,
    update_region_identity_services,
    update_region_network_services,
)
from tests.schemas.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_lower_string,
    random_network_service_name,
    random_url,
)


def get_block_storage_quota() -> BlockStorageQuotaCreateExtended:
    """Fixture with an SLA without projects."""
    return BlockStorageQuotaCreateExtended(
        gigabytes=randint(0, 100),
        per_volume_gigabytes=randint(0, 100),
        volumes=randint(1, 100),
        project=uuid4(),
    )


def get_compute_quota() -> ComputeQuotaCreateExtended:
    """Fixture with an SLA without projects."""
    return ComputeQuotaCreateExtended(
        cores=randint(0, 100),
        instances=randint(0, 100),
        ram=randint(1, 100),
        project=uuid4(),
    )


def get_flavor() -> FlavorCreateExtended:
    return FlavorCreateExtended(name=random_lower_string(), uuid=uuid4())


def get_image() -> ImageCreateExtended:
    return ImageCreateExtended(name=random_lower_string(), uuid=uuid4())


def get_network() -> NetworkCreateExtended:
    return NetworkCreateExtended(name=random_lower_string(), uuid=uuid4())


def get_network_quota() -> NetworkQuotaCreateExtended:
    """Fixture with an SLA without projects."""
    return NetworkQuotaCreateExtended(
        public_ips=randint(0, 100),
        networks=randint(0, 100),
        ports=randint(1, 100),
        security_groups=randint(1, 100),
        security_group_rules=randint(1, 100),
        project=uuid4(),
    )


@case(tags=["endpoint"])
@parametrize(equal=[True, False])
def case_endpoint(equal: bool) -> bool:
    return equal


@case(tags=["quotas"])
@parametrize(presence=[True, False])
def case_quota(presence: bool) -> bool:
    return presence


@case(tags=["resource"])
@parametrize(equal=[True, False])
def case_net_rel(equal: bool) -> Tuple[str, bool]:
    return equal


@parametrize_with_cases("equal_endpoint", cases=".", has_tag="endpoint")
@parametrize_with_cases("with_quota", cases=".", has_tag="quotas")
def test_update_region_block_storage_service(
    equal_endpoint: bool, with_quota: bool
) -> None:
    old_srv = BlockStorageServiceCreateExtended(
        endpoint=random_url(),
        name=random_block_storage_service_name(),
        quotas=[get_block_storage_quota()] if with_quota else [],
    )
    new_srv = BlockStorageServiceCreateExtended(
        endpoint=old_srv.endpoint if equal_endpoint else random_url(),
        name=random_block_storage_service_name(),
        quotas=[get_block_storage_quota()] if with_quota else [],
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_block_storage_services(
        current_services=current_services, new_service=new_srv
    )
    if equal_endpoint:
        assert len(current_services) == 1
        curr_srv = current_services[0]
        assert curr_srv.endpoint == old_srv.endpoint
        assert curr_srv.description == old_srv.description
        assert curr_srv.name == old_srv.name
        assert curr_srv.type == old_srv.type
        new_quotas = [*old_srv.quotas, *new_srv.quotas]
        assert len(curr_srv.quotas) == len(new_quotas)
    else:
        assert len(current_services) == 2
        assert current_services[0].endpoint == old_srv.endpoint
        assert current_services[0].description == old_srv.description
        assert current_services[0].name == old_srv.name
        assert current_services[0].type == old_srv.type
        assert len(current_services[0].quotas) == len(old_srv.quotas)
        assert current_services[1].endpoint == new_srv.endpoint
        assert current_services[1].description == new_srv.description
        assert current_services[1].name == new_srv.name
        assert current_services[1].type == new_srv.type
        assert len(current_services[1].quotas) == len(new_srv.quotas)


@parametrize_with_cases("equal_endpoint", cases=".", has_tag="endpoint")
@parametrize_with_cases("with_quota", cases=".", has_tag="quotas")
def test_update_region_compute_service(equal_endpoint: bool, with_quota: bool) -> None:
    old_srv = ComputeServiceCreateExtended(
        endpoint=random_url(),
        name=random_compute_service_name(),
        quotas=[get_compute_quota()] if with_quota else [],
    )
    new_srv = ComputeServiceCreateExtended(
        endpoint=old_srv.endpoint if equal_endpoint else random_url(),
        name=random_compute_service_name(),
        quotas=[get_compute_quota()] if with_quota else [],
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_compute_services(
        current_services=current_services, new_service=new_srv
    )
    if equal_endpoint:
        assert len(current_services) == 1
        curr_srv = current_services[0]
        assert curr_srv.endpoint == old_srv.endpoint
        assert curr_srv.description == old_srv.description
        assert curr_srv.name == old_srv.name
        assert curr_srv.type == old_srv.type
        new_quotas = [*old_srv.quotas, *new_srv.quotas]
        assert len(curr_srv.quotas) == len(new_quotas)
    else:
        assert len(current_services) == 2
        assert current_services[0].endpoint == old_srv.endpoint
        assert current_services[0].description == old_srv.description
        assert current_services[0].name == old_srv.name
        assert current_services[0].type == old_srv.type
        assert len(current_services[0].quotas) == len(old_srv.quotas)
        assert current_services[1].endpoint == new_srv.endpoint
        assert current_services[1].description == new_srv.description
        assert current_services[1].name == new_srv.name
        assert current_services[1].type == new_srv.type
        assert len(current_services[1].quotas) == len(new_srv.quotas)


@parametrize_with_cases("equal_endpoint", cases=".", has_tag="endpoint")
def test_update_region_identity_service(equal_endpoint: bool) -> None:
    old_srv = IdentityServiceCreate(
        endpoint=random_url(),
        name=random_identity_service_name(),
    )
    new_srv = IdentityServiceCreate(
        endpoint=old_srv.endpoint if equal_endpoint else random_url(),
        name=random_identity_service_name(),
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_identity_services(
        current_services=current_services, new_service=new_srv
    )
    if equal_endpoint:
        assert len(current_services) == 1
        curr_srv = current_services[0]
        assert curr_srv.endpoint == old_srv.endpoint
        assert curr_srv.description == old_srv.description
        assert curr_srv.name == old_srv.name
        assert curr_srv.type == old_srv.type
    else:
        assert len(current_services) == 2
        assert current_services[0].endpoint == old_srv.endpoint
        assert current_services[0].description == old_srv.description
        assert current_services[0].name == old_srv.name
        assert current_services[0].type == old_srv.type
        assert current_services[1].endpoint == new_srv.endpoint
        assert current_services[1].description == new_srv.description
        assert current_services[1].name == new_srv.name
        assert current_services[1].type == new_srv.type


@parametrize_with_cases("equal_endpoint", cases=".", has_tag="endpoint")
@parametrize_with_cases("with_quota", cases=".", has_tag="quotas")
def test_update_region_network_service(equal_endpoint: bool, with_quota: bool) -> None:
    old_srv = NetworkServiceCreateExtended(
        endpoint=random_url(),
        name=random_network_service_name(),
        quotas=[get_network_quota()] if with_quota else [],
    )
    new_srv = NetworkServiceCreateExtended(
        endpoint=old_srv.endpoint if equal_endpoint else random_url(),
        name=random_network_service_name(),
        quotas=[get_network_quota()] if with_quota else [],
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_network_services(
        current_services=current_services, new_service=new_srv
    )
    if equal_endpoint:
        assert len(current_services) == 1
        curr_srv = current_services[0]
        assert curr_srv.endpoint == old_srv.endpoint
        assert curr_srv.description == old_srv.description
        assert curr_srv.name == old_srv.name
        assert curr_srv.type == old_srv.type
        new_quotas = [*old_srv.quotas, *new_srv.quotas]
        assert len(curr_srv.quotas) == len(new_quotas)
        new_quotas = [*old_srv.quotas, *new_srv.quotas]
        assert len(curr_srv.quotas) == len(new_quotas)
    else:
        assert len(current_services) == 2
        assert current_services[0].endpoint == old_srv.endpoint
        assert current_services[0].description == old_srv.description
        assert current_services[0].name == old_srv.name
        assert current_services[0].type == old_srv.type
        assert len(current_services[0].quotas) == len(old_srv.quotas)
        assert current_services[1].endpoint == new_srv.endpoint
        assert current_services[1].description == new_srv.description
        assert current_services[1].name == new_srv.name
        assert current_services[1].type == new_srv.type
        assert len(current_services[1].quotas) == len(new_srv.quotas)


@parametrize_with_cases("equal", cases=".", has_tag="resource")
def test_update_region_compute_service_with_flavors(equal: bool) -> None:
    flavor1 = get_flavor()
    old_srv = ComputeServiceCreateExtended(
        endpoint=random_url(), name=random_compute_service_name(), flavors=[flavor1]
    )
    flavor2 = flavor1 if equal else get_flavor()
    new_srv = ComputeServiceCreateExtended(
        endpoint=old_srv.endpoint, name=random_compute_service_name(), flavors=[flavor2]
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_compute_services(
        current_services=current_services, new_service=new_srv
    )
    assert len(current_services) == 1
    assert len(current_services[0].flavors) == (1 if equal else 2)


@parametrize_with_cases("equal", cases=".", has_tag="resource")
def test_update_region_compute_service_with_images(equal: bool) -> None:
    image1 = get_image()
    old_srv = ComputeServiceCreateExtended(
        endpoint=random_url(), name=random_compute_service_name(), images=[image1]
    )
    image2 = image1 if equal else get_image()
    new_srv = ComputeServiceCreateExtended(
        endpoint=old_srv.endpoint, name=random_compute_service_name(), images=[image2]
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_compute_services(
        current_services=current_services, new_service=new_srv
    )
    assert len(current_services) == 1
    assert len(current_services[0].images) == (1 if equal else 2)


@parametrize_with_cases("equal", cases=".", has_tag="resource")
def test_update_region_network_service_with_networks(equal: bool) -> None:
    item1 = get_network()
    old_srv = NetworkServiceCreateExtended(
        endpoint=random_url(), name=random_network_service_name(), networks=[item1]
    )
    item2 = item1 if equal else get_network()
    new_srv = NetworkServiceCreateExtended(
        endpoint=old_srv.endpoint, name=random_network_service_name(), networks=[item2]
    )
    current_services = [copy.deepcopy(old_srv)]
    update_region_network_services(
        current_services=current_services, new_service=new_srv
    )
    assert len(current_services) == 1
    assert len(current_services[0].networks) == (1 if equal else 2)
