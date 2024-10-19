import pytest
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Kubernetes, Openstack
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
def test_get_matching_auth_method(provider_thread_item: ProviderThread) -> None:
    endpoint = provider_thread_item.issuers[0].endpoint
    provider_thread_item.provider_conf.identity_providers[0].endpoint = endpoint
    item = provider_thread_item.get_auth_method_matching_issuer(endpoint)
    assert item is not None
    assert isinstance(item, AuthMethod)
    assert item.endpoint == endpoint


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_no_match(provider_thread_item: ProviderThread) -> None:
    endpoint = provider_thread_item.issuers[0].endpoint
    trusted_endpoints = [
        i.endpoint for i in provider_thread_item.provider_conf.identity_providers
    ]
    msg = f"No identity provider matches endpoint `{endpoint}` in "
    msg += f"provider's trusted identity providers {trusted_endpoints}."
    with pytest.raises(ValueError, match="No identity provider matches endpoint"):
        provider_thread_item.get_auth_method_matching_issuer(endpoint)
