import copy
from typing import Tuple
from uuid import uuid4

from app.provider.schemas_extended import IdentityProviderCreateExtended
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.core import update_identity_providers
from tests.schemas.utils import random_lower_string, random_url


class CaseEquals:
    @parametrize(endpoint=[True, False])
    @parametrize(name=[True, False])
    def case_endpoint(self, endpoint: bool, name: bool) -> Tuple[bool, bool]:
        return endpoint, name


@parametrize_with_cases("equal_endpoint, equal_name", cases=CaseEquals)
def test_update_identity_providers(
    identity_provider_create: IdentityProviderCreateExtended,
    equal_endpoint: bool,
    equal_name: bool,
) -> None:
    """When updating the list of the identity providers, we can find duplicates.

    When finding duplicates, we can update the list of the user groups or leave it
    unchanged.
    """
    old_issuer = identity_provider_create
    new_issuer = copy.deepcopy(identity_provider_create)
    new_issuer.user_groups[0].sla.doc_uuid = uuid4()
    if not equal_endpoint:
        new_issuer.endpoint = random_url()
    if not equal_name:
        new_issuer.user_groups[0].name = random_lower_string()

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
        new_user_groups = 1 if equal_name else 2
        assert len(curr_iss.user_groups) == new_user_groups
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
