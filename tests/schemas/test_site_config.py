from typing import Any, List, Union
from uuid import uuid4

import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.config import SiteConfig
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import AuthMethod, Kubernetes, Openstack, Project
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


def get_invalid_value(*, case: str, item: Any) -> Union[Any, List[Any], None]:
    if case.endswith("none"):
        return None
    elif case.endswith("empty"):
        return item
    elif case.endswith("single"):
        return item
    elif case.endswith("duplicate"):
        return [item, item]
    return None


@case(tags=["type"])
@parametrize(attr=["openstack", "kubernetes"])
def case_provider_type(attr: str) -> str:
    return attr


@case(tags=["invalid"])
@parametrize(
    attr=[
        "issuer_none",
        "issuer_empty",
        "issuer_single",
        "issuer_duplicate",
        "openstack_none",
        "openstack_single",
        "openstack_duplicate",
        "kubernetes_none",
        "kubernetes_single",
        "kubernetes_duplicate",
    ]
)
def case_invalid_attr(attr: bool) -> bool:
    return attr


@pytest.fixture
def project() -> Project:
    return Project(id=uuid4(), sla=uuid4())


@pytest.fixture()
def auth_method() -> AuthMethod:
    return AuthMethod(
        name=random_lower_string(),
        protocol=random_lower_string(),
        endpoint=random_url(),
    )


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
def sla() -> SLA:
    """Fixture with an SLA without projects."""
    start_date, end_date = random_start_end_dates()
    return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


@pytest.fixture
def user_group(sla: SLA) -> UserGroup:
    """Fixture with an UserGroup without projects."""
    return UserGroup(name=random_lower_string(), slas=[sla])


@pytest.fixture
def issuer(user_group: UserGroup) -> Issuer:
    return Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        user_groups=[user_group],
    )


@parametrize_with_cases("provider_type", cases=".", has_tag="type")
def test_site_config_schema(
    provider_type: str,
    issuer: Issuer,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    d = {"trusted_idps": [issuer]}
    if provider_type == "openstack":
        d["openstack"] = [openstack_provider]
    elif provider_type == "kubernetes":
        d["kubernetes"] = [kubernetes_provider]
    item = SiteConfig(**d)
    assert item.trusted_idps == d.get("trusted_idps")
    assert item.openstack == d.get("openstack", [])
    assert item.kubernetes == d.get("kubernetes", [])


@parametrize_with_cases("case", cases=".", has_tag="invalid")
def test_site_config_invalid_schema(
    case: str,
    issuer: Issuer,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    issuer_list = [issuer]
    openstack_list = [openstack_provider]
    kubernetes_list = [kubernetes_provider]
    if case.startswith("issuer"):
        issuer_list = get_invalid_value(case=case, item=issuer)
    if case.startswith("openstack"):
        openstack_list = get_invalid_value(case=case, item=openstack_provider)
    elif case.startswith("kubernetes"):
        kubernetes_list = get_invalid_value(case=case, item=kubernetes_provider)

    d = {
        "trusted_idps": issuer_list,
        "openstack": openstack_list,
        "kubernetes": kubernetes_list,
    }
    with pytest.raises(ValueError):
        SiteConfig(**d)
