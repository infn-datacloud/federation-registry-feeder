from typing import Literal
from unittest.mock import Mock, patch

from fedreg.v1.provider.enum import ProviderStatus
from fedreg.v1.provider.schemas_extended import ProjectCreate
from pytest_cases import case, parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.core import ProviderThread
from src.providers.openstack import OpenstackProviderError
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


class CaseProviderStatus:
    @case(tags="active")
    def case_active(self) -> Literal["active"]:
        return ProviderStatus.ACTIVE.value

    @case(tags="inactive")
    def case_maintenance(self) -> Literal["maintenance"]:
        return ProviderStatus.MAINTENANCE.value


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


class CaseThreadConnError:
    def case_not_implemented(self) -> NotImplementedError:
        return NotImplementedError()

    def case_openstack_data(self) -> OpenstackProviderError:
        return OpenstackProviderError()


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("status", cases=CaseProviderStatus, has_tag="inactive")
def test_get_non_active_provider(provider_thread_item: ProviderThread, status: str):
    """Provider is not Active or it has no project matching SLA in the issuer."""
    provider_thread_item.provider_conf.status = status

    item = provider_thread_item.get_provider()

    assert not provider_thread_item.error

    assert item is not None
    assert isinstance(item, tuple)
    assert len(item) == 3
    provider_conf = item[0]
    assert provider_conf == provider_thread_item.provider_conf
    connections_data = item[1]
    assert len(connections_data) == 0
    assert not item[2]


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_get_provider(
    provider_thread_item: ProviderThread, project_create: ProjectCreate
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    project_create.uuid = provider_thread_item.provider_conf.projects[0].id
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint

    with patch("src.providers.core.ConnectionThread.get_provider_data"):
        item = provider_thread_item.get_provider()

    assert not provider_thread_item.error

    assert item is not None
    assert isinstance(item, tuple)
    assert len(item) == 3
    provider_conf = item[0]
    assert provider_conf == provider_thread_item.provider_conf
    connections_data = item[1]
    assert len(connections_data) == 1
    assert not item[2]


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_no_sla_match(provider_thread_item: ProviderThread):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    item = provider_thread_item.get_provider()

    assert item is not None
    assert isinstance(item, tuple)
    assert len(item) == 3
    provider_conf = item[0]
    assert provider_conf == provider_thread_item.provider_conf
    connections_data = item[1]
    assert len(connections_data) == 0
    assert item[2]


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_no_issuer_and_auth_method_match(provider_thread_item: ProviderThread):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    item = provider_thread_item.get_provider()

    assert item is not None
    assert isinstance(item, tuple)
    assert len(item) == 3
    provider_conf = item[0]
    assert provider_conf == provider_thread_item.provider_conf
    connections_data = item[1]
    assert len(connections_data) == 0
    assert item[2]


@patch("src.providers.core.ConnectionThread.__init__")
@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_get_error_from_thread_connection(
    mock_conn_thread_init: Mock, provider_thread_item: ProviderThread
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    mock_conn_thread_init.side_effect = AssertionError()

    item = provider_thread_item.get_provider()

    assert item is not None
    assert isinstance(item, tuple)
    assert len(item) == 3
    provider_conf = item[0]
    assert provider_conf == provider_thread_item.provider_conf
    connections_data = item[1]
    assert len(connections_data) == 0
    assert item[2]


@patch("src.providers.core.ConnectionThread.get_provider_data")
@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("error", cases=CaseThreadConnError)
def test_get_error_from_get_provider_components(
    mock_get_components: Mock,
    provider_thread_item: ProviderThread,
    error: NotImplementedError | OpenstackProviderError,
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    mock_get_components.side_effect = error

    item = provider_thread_item.get_provider()

    assert item is not None
    assert isinstance(item, tuple)
    assert len(item) == 3
    provider_conf = item[0]
    assert provider_conf == provider_thread_item.provider_conf
    connections_data = item[1]
    assert len(connections_data) == 0
    assert item[2]
