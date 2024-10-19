import pytest
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
def test_get_matching_issuer(provider_thread_item: ProviderThread) -> None:
    sla = provider_thread_item.provider_conf.projects[0].sla
    provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid = sla
    item = provider_thread_item.get_issuer_matching_project(sla)
    assert item is not None
    assert isinstance(item, Issuer)
    assert len(item.user_groups) == 1
    assert len(item.user_groups[0].slas) == 1
    assert item.user_groups[0].slas[0].doc_uuid == sla


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_no_matching_sla(provider_thread_item: ProviderThread) -> None:
    sla = provider_thread_item.provider_conf.projects[0].sla
    with pytest.raises(ValueError, match="No SLA matches project's doc_uuid"):
        provider_thread_item.get_issuer_matching_project(sla)
