import os
from uuid import uuid4

import pytest
from fed_reg.provider.enum import ProviderType
from fed_reg.provider.schemas_extended import (
    AuthMethodCreate,
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
    RegionCreateExtended,
    SLACreateExtended,
    UserGroupCreateExtended,
)
from fed_reg.service.enum import ObjectStoreServiceName
from pytest_cases import parametrize

from tests.schemas.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_lower_string,
    random_network_service_name,
    random_url,
    sla_dict,
)


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    """Clear the OS environment."""
    os.environ.clear()


@pytest.fixture
def project_create() -> ProjectCreate:
    """Fixture with a ProjectCreate."""
    return ProjectCreate(uuid=uuid4(), name=random_lower_string())


@pytest.fixture
def block_storage_service_create() -> BlockStorageServiceCreateExtended:
    """Fixture with a BlockStorageServiceCreateExtended."""
    return BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=random_block_storage_service_name()
    )


@pytest.fixture
def compute_service_create() -> ComputeServiceCreateExtended:
    """Fixture with a ComputeServiceCreateExtended."""
    return ComputeServiceCreateExtended(
        endpoint=random_url(), name=random_compute_service_name()
    )


@pytest.fixture
def identity_service_create() -> IdentityServiceCreate:
    """Fixture with an IdentityServiceCreate."""
    return IdentityServiceCreate(
        endpoint=random_url(), name=random_identity_service_name()
    )


@pytest.fixture
def network_service_create() -> NetworkServiceCreateExtended:
    """Fixture with a NetworkServiceCreateExtended."""
    return NetworkServiceCreateExtended(
        endpoint=random_url(), name=random_network_service_name()
    )


@pytest.fixture
def object_store_service_create() -> ObjectStoreServiceCreateExtended:
    """Fixture with a NetworkServiceCreateExtended."""
    return ObjectStoreServiceCreateExtended(
        endpoint=random_url(), name=ObjectStoreServiceName.OPENSTACK_SWIFT
    )


@pytest.fixture
def s3_service_create() -> ObjectStoreServiceCreateExtended:
    """Fixture with a NetworkServiceCreateExtended."""
    return ObjectStoreServiceCreateExtended(
        endpoint=random_url(), name=ObjectStoreServiceName.OPENSTACK_SWIFT_S3
    )


@pytest.fixture
@parametrize(
    s=[
        block_storage_service_create,
        compute_service_create,
        identity_service_create,
        network_service_create,
    ]
)
def service_create(
    s: BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | IdentityServiceCreate
    | NetworkServiceCreateExtended,
) -> (
    BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | IdentityServiceCreate
    | NetworkServiceCreateExtended
):
    """Parametrized fixture with all possible services.

    BlockStorageServiceCreateExtended, ComputeServiceCreateExtended,
    IdentityServiceCreate and NetworkServiceCreateExtended.
    """
    return s


@pytest.fixture
def sla_create() -> SLACreateExtended:
    """Fixture with an SLACreateExtended."""
    return SLACreateExtended(**sla_dict(), project=uuid4())


@pytest.fixture
def user_group_create(sla_create: SLACreateExtended) -> UserGroupCreateExtended:
    """Fixture with a UserGroupCreateExtended."""
    return UserGroupCreateExtended(name=random_lower_string(), sla=sla_create)


@pytest.fixture
def auth_method_create() -> AuthMethodCreate:
    return AuthMethodCreate(
        idp_name=random_lower_string(), protocol=random_lower_string()
    )


@pytest.fixture
def identity_provider_create(
    auth_method_create: AuthMethodCreate, user_group_create: UserGroupCreateExtended
) -> IdentityProviderCreateExtended:
    """Fixture with an IdentityProviderCreateExtended."""
    return IdentityProviderCreateExtended(
        user_groups=[user_group_create],
        endpoint=random_url(),
        group_claim=random_lower_string(),
        relationship=auth_method_create,
    )


@pytest.fixture
def region_create(
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    identity_service_create: IdentityServiceCreate,
    network_service_create: NetworkServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
):
    """Fixture with a RegionCreateExtended"""
    return RegionCreateExtended(
        name=random_lower_string(),
        block_storage_services=[block_storage_service_create],
        compute_services=[compute_service_create],
        identity_services=[identity_service_create],
        network_services=[network_service_create],
        object_store_services=[s3_service_create],
    )


@pytest.fixture
def provider_create(
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
):
    identity_provider_create.user_groups[0].sla.project = project_create.uuid
    return ProviderCreateExtended(
        name=random_lower_string(),
        type=ProviderType.OS,
        identity_providers=[identity_provider_create],
        regions=[region_create],
        projects=[project_create],
    )
