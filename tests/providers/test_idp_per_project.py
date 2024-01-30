from uuid import uuid4

import pytest

from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Project
from src.providers.core import (
    get_identity_provider_info_for_project,
    get_identity_provider_with_auth_method,
)
from tests.schemas.utils import random_lower_string, random_url


def test_get_ipd_with_auth_method(issuer: Issuer) -> None:
    auth_method = AuthMethod(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    user_group = issuer.user_groups[0]
    sla = user_group.slas[0]
    item = get_identity_provider_with_auth_method(
        auth_methods=[auth_method],
        issuer=issuer,
        user_group=user_group,
        sla=sla,
        project=uuid4().hex,
    )
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.relationship
    assert item.relationship.idp_name == auth_method.idp_name
    assert item.relationship.protocol == auth_method.protocol


def test_fail_update_issuer(issuer: Issuer) -> None:
    auth_method = AuthMethod(
        endpoint=random_url(),
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    user_group = issuer.user_groups[0]
    sla = user_group.slas[0]
    with pytest.raises(ValueError):
        get_identity_provider_with_auth_method(
            auth_methods=[auth_method],
            issuer=issuer,
            user_group=user_group,
            sla=sla,
            project=uuid4().hex,
        )


def test_retrieve_idp_for_target_project(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=issuer.user_groups[0].slas[0].doc_uuid)
    auth_method = AuthMethod(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    item, token = get_identity_provider_info_for_project(
        issuers=[issuer], auth_methods=[auth_method], project=project
    )
    assert token == issuer.token
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.relationship
    assert item.relationship.idp_name == auth_method.idp_name
    assert item.relationship.protocol == auth_method.protocol
    assert item.user_groups[0].sla.project == project.id


def test_no_matching_sla(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=uuid4())
    auth_method = AuthMethod(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    with pytest.raises(ValueError):
        get_identity_provider_info_for_project(
            issuers=[issuer], auth_methods=[auth_method], project=project
        )
