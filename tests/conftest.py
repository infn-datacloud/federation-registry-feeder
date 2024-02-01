import os
from typing import Union
from uuid import uuid4

import pytest
from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
)
from pytest_cases import parametrize

from src.config import APIVersions, Settings, URLs
from src.crud import CRUD
from src.models.config import SiteConfig
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import (
    AuthMethod,
    Kubernetes,
    Limits,
    Openstack,
    PerRegionProps,
    PrivateNetProxy,
    Project,
    Region,
)
from src.utils import get_read_write_headers
from tests.schemas.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_identity_service_name,
    random_ip,
    random_lower_string,
    random_network_service_name,
    random_provider_type,
    random_start_end_dates,
    random_url,
)


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    """Clear the OS environment."""
    os.environ.clear()


@pytest.fixture
def crud() -> CRUD:
    """Fixture with a CRUD object.

    The CRUD object is used to interact with the federation-registry API.
    """
    read_header, write_header = get_read_write_headers(token=random_lower_string())
    return CRUD(url=random_url(), read_headers=read_header, write_headers=write_header)


@pytest.fixture
def api_ver() -> APIVersions:
    """Fixture with an APIVersions object.

    The APIVersions object is used to store the API versions to use when interacting
    with the federation-registry API.
    """
    return APIVersions()


@pytest.fixture
def settings(api_ver: APIVersions) -> Settings:
    """Fixture with a Settings object.

    The Settings object stores the project settings.
    """
    return Settings(api_ver=api_ver)


@pytest.fixture
def service_endpoints() -> URLs:
    """Fixture with a URLs object.

    The URLs object stores the federation-registry service endpoints.
    """
    base_url = random_url()
    return URLs(**{k: os.path.join(base_url, k) for k in URLs.__fields__.keys()})


# Identity Providers configurations


@pytest.fixture
def sla() -> SLA:
    """Fixture with an SLA without projects."""
    start_date, end_date = random_start_end_dates()
    return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


@pytest.fixture
def user_group(sla: SLA) -> UserGroup:
    """Fixture with a UserGroup with one SLA."""
    return UserGroup(name=random_lower_string(), slas=[sla])


@pytest.fixture
def issuer(user_group: UserGroup) -> Issuer:
    """Fixture with an Issuer with one UserGroup."""
    return Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        user_groups=[user_group],
    )


# Providers configurations


@pytest.fixture
def auth_method() -> AuthMethod:
    """Fixture with an AuthMethod."""
    return AuthMethod(
        name=random_lower_string(),
        protocol=random_lower_string(),
        endpoint=random_url(),
    )


@pytest.fixture
def limits() -> Limits:
    """Fixture with an empty Limits object."""
    return Limits()


@pytest.fixture
def net_proxy() -> PrivateNetProxy:
    """Fixture with an PrivateNetProxy."""
    return PrivateNetProxy(ip=random_ip(), user=random_lower_string())


@pytest.fixture
def per_region_props() -> PerRegionProps:
    """Fixture with a minimal PerRegionProps object."""
    return PerRegionProps(region_name=random_lower_string())


@pytest.fixture
def project() -> Project:
    """Fixture with a Project with an SLA."""
    return Project(id=uuid4(), sla=uuid4())


@pytest.fixture
def region() -> Region:
    """Fixture with a Region."""
    return Region(name=random_lower_string())


@pytest.fixture
def openstack_provider(auth_method: AuthMethod, project: Project) -> Openstack:
    """Fixture with an Openstack provider.

    It has an authentication method and a project.
    """
    return Openstack(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[auth_method],
        projects=[project],
    )


@pytest.fixture
def kubernetes_provider(auth_method: AuthMethod, project: Project) -> Kubernetes:
    """Fixture with a Kubernetes provider.

    It has an authentication method and a project.
    """
    return Kubernetes(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[auth_method],
        projects=[project],
    )


@pytest.fixture
def site_config(issuer: Issuer) -> SiteConfig:
    """Fixture with a SiteConfig with an Issuer and no providers."""
    return SiteConfig(trusted_idps=[issuer])


# Federation-Registry Creation Items


@pytest.fixture
def provider_create() -> ProviderCreateExtended:
    """Fixture with a ProviderCreateExtended."""
    return ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )


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
@parametrize(
    s=[
        block_storage_service_create,
        compute_service_create,
        identity_service_create,
        network_service_create,
    ]
)
def service_create(
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
    """Parametrized fixture with all possible services.

    BlockStorageServiceCreateExtended, ComputeServiceCreateExtended,
    IdentityServiceCreate and NetworkServiceCreateExtended.
    """
    return s
