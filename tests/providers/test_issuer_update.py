import copy
from uuid import uuid4

from app.auth_method.schemas import AuthMethodCreate
from app.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    SLACreateExtended,
    UserGroupCreateExtended,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.core import update_identity_providers
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@parametrize(equal=[True, False])
def case_endpoint(equal: bool) -> bool:
    return equal


@parametrize_with_cases("equal_endpoint", cases=".")
def test_update_identity_providers(equal_endpoint: bool) -> None:
    start_date, end_date = random_start_end_dates()
    old_sla = SLACreateExtended(
        doc_uuid=uuid4(), start_date=start_date, end_date=end_date, project=uuid4()
    )
    old_user_group = UserGroupCreateExtended(name=random_lower_string(), sla=old_sla)
    old_issuer = IdentityProviderCreateExtended(
        endpoint=random_url(),
        group_claim=random_lower_string(),
        relationship=AuthMethodCreate(
            idp_name=random_lower_string(), protocol=random_lower_string()
        ),
        user_groups=[old_user_group],
    )

    start_date, end_date = random_start_end_dates()
    new_sla = SLACreateExtended(
        doc_uuid=uuid4(), start_date=start_date, end_date=end_date, project=uuid4()
    )
    new_user_group = UserGroupCreateExtended(name=random_lower_string(), sla=new_sla)
    new_issuer = IdentityProviderCreateExtended(
        endpoint=old_issuer.endpoint if equal_endpoint else random_url(),
        group_claim=random_lower_string(),
        relationship=AuthMethodCreate(
            idp_name=random_lower_string(), protocol=random_lower_string()
        ),
        user_groups=[new_user_group],
    )
    current_issuers = update_identity_providers(
        new_issuers=[copy.deepcopy(old_issuer), copy.deepcopy(new_issuer)]
    )
    if equal_endpoint:
        assert len(current_issuers) == 1
        curr_iss = current_issuers[0]
        assert curr_iss.endpoint == old_issuer.endpoint
        assert curr_iss.description == old_issuer.description
        assert curr_iss.group_claim == old_issuer.group_claim
        assert curr_iss.relationship == old_issuer.relationship
        new_user_groups = [*old_issuer.user_groups, *new_issuer.user_groups]
        assert len(curr_iss.user_groups) == len(new_user_groups)
    else:
        assert len(current_issuers) == 2
        assert current_issuers[0].endpoint == old_issuer.endpoint
        assert current_issuers[0].description == old_issuer.description
        assert current_issuers[0].group_claim == old_issuer.group_claim
        assert current_issuers[0].relationship == old_issuer.relationship
        assert len(current_issuers[0].user_groups) == len(old_issuer.user_groups)
        assert current_issuers[1].endpoint == new_issuer.endpoint
        assert current_issuers[1].description == new_issuer.description
        assert current_issuers[1].group_claim == new_issuer.group_claim
        assert current_issuers[1].relationship == new_issuer.relationship
        assert len(current_issuers[1].user_groups) == len(new_issuer.user_groups)
