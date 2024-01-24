from uuid import uuid4

import pytest

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import Project, TrustedIDP
from src.providers.openstack import (
    get_identity_provider_for_project,
    update_issuer_auth_method,
)
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@pytest.fixture
def sla() -> SLA:
    start_date, end_date = random_start_end_dates()
    return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


@pytest.fixture
def user_group(sla: SLA) -> UserGroup:
    return UserGroup(name=random_lower_string(), slas=[sla])


@pytest.fixture
def issuer(user_group: UserGroup) -> Issuer:
    return Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        user_groups=[user_group],
    )


def test_update_issuer(issuer: Issuer) -> None:
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    item = update_issuer_auth_method(issuer=issuer, auth_methods=[idp])
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.token == issuer.token
    assert item.relationship
    assert item.relationship.idp_name == idp.idp_name
    assert item.relationship.protocol == idp.protocol


def test_fail_update_issuer(issuer: Issuer) -> None:
    idp = TrustedIDP(
        endpoint=random_url(),
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    with pytest.raises(ValueError):
        update_issuer_auth_method(issuer=issuer, auth_methods=[idp])


def test_retrieve_idp_for_target_project(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=issuer.user_groups[0].slas[0].doc_uuid)
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    item = get_identity_provider_for_project(
        issuers=[issuer], trusted_idps=[idp], project=project
    )
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.token == issuer.token
    assert item.relationship
    assert item.relationship.idp_name == idp.idp_name
    assert item.relationship.protocol == idp.protocol
    assert len(item.user_groups[0].slas[0].projects) == 1
    assert item.user_groups[0].slas[0].projects[0] == project.id


def test_project_already_in_sla(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=issuer.user_groups[0].slas[0].doc_uuid)
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    issuer.user_groups[0].slas[0].projects.append(project.id)
    item = get_identity_provider_for_project(
        issuers=[issuer], trusted_idps=[idp], project=project
    )
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.token == issuer.token
    assert item.relationship
    assert item.relationship.idp_name == idp.idp_name
    assert item.relationship.protocol == idp.protocol
    assert len(item.user_groups[0].slas[0].projects) == 1
    assert item.user_groups[0].slas[0].projects[0] == project.id


def test_not_matching_sla(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=uuid4())
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    with pytest.raises(ValueError):
        get_identity_provider_for_project(
            issuers=[issuer], trusted_idps=[idp], project=project
        )
