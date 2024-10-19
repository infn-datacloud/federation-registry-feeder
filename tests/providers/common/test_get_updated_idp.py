from uuid import uuid4

from fed_reg.provider.schemas_extended import IdentityProviderCreateExtended
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.core import ProviderThread
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
    sla_dict,
    user_group_dict,
)


class CaseProviderThread:
    def case_openstack(self) -> ProviderThread:
        provider = Openstack(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])

    def case_k8s(self) -> ProviderThread:
        provider = Kubernetes(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_add_new_idp(
    provider_thread_item: ProviderThread,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    item = provider_thread_item.get_updated_identity_provider(
        current_idp=None, new_idp=identity_provider_create
    )
    assert item == identity_provider_create


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_new_idp_matches_old_ons(
    provider_thread_item: ProviderThread,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    item = provider_thread_item.get_updated_identity_provider(
        current_idp=identity_provider_create, new_idp=identity_provider_create
    )
    assert item == identity_provider_create


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_new_idp_has_new_group(
    provider_thread_item: ProviderThread,
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
    item = provider_thread_item.get_updated_identity_provider(
        current_idp=current_idp, new_idp=identity_provider_create
    )
    assert item.endpoint == current_idp.endpoint
    assert item.group_claim == current_idp.group_claim
    assert item.relationship == current_idp.relationship
    assert len(item.user_groups) == 2
    assert current_idp.user_groups[0] in item.user_groups
    assert identity_provider_create.user_groups[0] in item.user_groups
