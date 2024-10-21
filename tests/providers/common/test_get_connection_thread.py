from unittest.mock import Mock, patch

from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.core import ProviderThread
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    kubernetes_dict,
    openstack_dict,
    project_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string


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
            **kubernetes_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])


@patch("src.providers.core.ConnectionThread.__init__")
@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_get_error_from_thread_connection(
    mock_conn_thread_init: Mock,
    provider_thread_item: ProviderThread,
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    mock_conn_thread_init.side_effect = AssertionError

    item = provider_thread_item.get_connection_thread(
        project=provider_thread_item.provider_conf.projects[0],
        region=provider_thread_item.provider_conf.regions[0],
    )

    assert item is None


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_catch_value_error_from_no_matching_issuer(
    provider_thread_item: ProviderThread,
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    item = provider_thread_item.get_connection_thread(
        project=provider_thread_item.provider_conf.projects[0],
        region=provider_thread_item.provider_conf.regions[0],
    )
    assert item is None


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_catch_value_error_from_no_matching_sla(
    provider_thread_item: ProviderThread,
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    item = provider_thread_item.get_connection_thread(
        project=provider_thread_item.provider_conf.projects[0],
        region=provider_thread_item.provider_conf.regions[0],
    )
    assert item is None
