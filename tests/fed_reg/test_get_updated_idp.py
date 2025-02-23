from uuid import uuid4

from fedreg.provider.schemas_extended import IdentityProviderCreateExtended

from src.utils import get_updated_identity_provider
from tests.schemas.utils import sla_dict
from tests.utils import random_lower_string


def test_add_new_idp(
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    item = get_updated_identity_provider(
        current_idp=None, new_idp=identity_provider_create
    )
    assert item == identity_provider_create


def test_new_idp_matches_old_ons(
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    item = get_updated_identity_provider(
        current_idp=identity_provider_create, new_idp=identity_provider_create
    )
    assert item == identity_provider_create


def test_new_idp_has_new_group(
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    current_idp = IdentityProviderCreateExtended(
        **identity_provider_create.dict(exclude={"user_groups"}),
        user_groups=[
            {
                "name": random_lower_string(),
                "sla": {**sla_dict(), "project": uuid4()},
            }
        ],
    )
    item = get_updated_identity_provider(
        current_idp=current_idp, new_idp=identity_provider_create
    )
    assert item.endpoint == current_idp.endpoint
    assert item.group_claim == current_idp.group_claim
    assert item.relationship == current_idp.relationship
    assert len(item.user_groups) == 2
    assert current_idp.user_groups[0] in item.user_groups
    assert identity_provider_create.user_groups[0] in item.user_groups
