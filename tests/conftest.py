import os
from uuid import uuid4

import pytest
from app.provider.schemas_extended import ProviderCreateExtended

from src.config import APIVersions, Settings, URLs
from src.models.config import SiteConfig
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import (
    AuthMethod,
    Kubernetes,
    Limits,
    Openstack,
    PrivateNetProxy,
    Project,
    Region,
)
from tests.schemas.utils import (
    random_ip,
    random_lower_string,
    random_provider_type,
    random_start_end_dates,
    random_url,
)


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    os.environ.clear()


@pytest.fixture
def api_ver() -> APIVersions:
    return APIVersions()


@pytest.fixture
def settings(api_ver: APIVersions) -> Settings:
    return Settings(api_ver=api_ver)


@pytest.fixture
def service_endpoints() -> URLs:
    base_url = random_url()
    return URLs(**{k: os.path.join(base_url, k) for k in URLs.__fields__.keys()})


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


@pytest.fixture
def auth_method() -> AuthMethod:
    return AuthMethod(
        name=random_lower_string(),
        protocol=random_lower_string(),
        endpoint=random_url(),
    )


@pytest.fixture
def limits() -> Limits:
    return Limits()


@pytest.fixture
def net_proxy() -> PrivateNetProxy:
    return PrivateNetProxy(ip=random_ip(), user=random_lower_string())


@pytest.fixture
def project() -> Project:
    return Project(id=uuid4(), sla=uuid4())


@pytest.fixture
def region() -> Region:
    return Region(name=random_lower_string())


@pytest.fixture
def openstack_provider(auth_method: AuthMethod, project: Project) -> Openstack:
    return Openstack(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[auth_method],
        projects=[project],
    )


@pytest.fixture
def kubernetes_provider(auth_method: AuthMethod, project: Project) -> Kubernetes:
    return Kubernetes(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[auth_method],
        projects=[project],
    )


@pytest.fixture
def site_config(issuer: Issuer) -> SiteConfig:
    return SiteConfig(trusted_idps=[issuer])


@pytest.fixture
def provider_create() -> ProviderCreateExtended:
    return ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
