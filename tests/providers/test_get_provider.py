from typing import Literal
from unittest.mock import Mock, patch

from fed_reg.provider.enum import ProviderStatus
from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
    RegionCreateExtended,
)
from pytest_cases import case, parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.core import ProviderThread
from src.providers.openstack import OpenstackProviderException
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    kubernetes_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
    sla_dict,
    user_group_dict,
)


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
    def case_assertion(self) -> AssertionError:
        return AssertionError()

    def case_not_implemented(self) -> NotImplementedError:
        return NotImplementedError()

    def case_openstack_data(self) -> OpenstackProviderException:
        return OpenstackProviderException()


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("status", cases=CaseProviderStatus, has_tag="inactive")
def test_get_non_active_provider(provider_thread_item: ProviderThread, status: str):
    """Provider is not Active or it has no project matching SLA in the issuer."""
    provider_thread_item.provider_conf.status = status

    item = provider_thread_item.get_provider()

    assert not provider_thread_item.error

    assert item is not None
    assert isinstance(item, ProviderCreateExtended)
    assert item.description == provider_thread_item.provider_conf.description
    assert item.name == provider_thread_item.provider_conf.name
    assert item.type == provider_thread_item.provider_conf.type
    assert item.status == provider_thread_item.provider_conf.status
    assert item.is_public == provider_thread_item.provider_conf.is_public
    assert item.support_emails == provider_thread_item.provider_conf.support_emails
    assert len(item.regions) == 0
    assert len(item.projects) == 0
    assert len(item.identity_providers) == 0


@patch("src.providers.core.ConnectionThread.get_provider_components")
@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_get_provider(mock_siblings: Mock, provider_thread_item: ProviderThread):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    mock_siblings.return_value = (
        IdentityProviderCreateExtended(
            endpoint=provider_thread_item.issuers[0].endpoint,
            group_claim=provider_thread_item.issuers[0].group_claim,
            relationship={
                "protocol": provider_thread_item.provider_conf.identity_providers[
                    0
                ].protocol,
                "idp_name": provider_thread_item.provider_conf.identity_providers[
                    0
                ].idp_name,
            },
            user_groups=[
                {
                    "name": provider_thread_item.issuers[0].user_groups[0].name,
                    "sla": {
                        **provider_thread_item.issuers[0].user_groups[0].slas[0].dict(),
                        "project": provider_thread_item.provider_conf.projects[0].id,
                    },
                }
            ],
        ),
        ProjectCreate(
            name=random_lower_string(),
            uuid=provider_thread_item.provider_conf.projects[0].id,
        ),
        RegionCreateExtended(name=provider_thread_item.provider_conf.regions[0].name),
    )
    item = provider_thread_item.get_provider()

    mock_siblings.assert_called_once()
    assert not provider_thread_item.error

    assert isinstance(item, ProviderCreateExtended)
    assert item.description == provider_thread_item.provider_conf.description
    assert item.name == provider_thread_item.provider_conf.name
    assert item.type == provider_thread_item.provider_conf.type
    assert item.status == provider_thread_item.provider_conf.status
    assert item.is_public == provider_thread_item.provider_conf.is_public
    assert item.support_emails == provider_thread_item.provider_conf.support_emails
    assert len(item.regions) == 1
    assert item.regions[0].name == provider_thread_item.provider_conf.regions[0].name
    assert len(item.projects) == 1
    assert item.projects[0].uuid == provider_thread_item.provider_conf.projects[0].id
    assert len(item.identity_providers) == 1
    assert (
        item.identity_providers[0].endpoint == provider_thread_item.issuers[0].endpoint
    )
    assert (
        item.identity_providers[0].group_claim
        == provider_thread_item.issuers[0].group_claim
    )
    user_groups = item.identity_providers[0].user_groups
    assert len(user_groups) == 1
    assert user_groups[0].name == provider_thread_item.issuers[0].user_groups[0].name
    sla = user_groups[0].sla
    assert sla is not None
    assert (
        sla.doc_uuid == provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    assert (
        sla.start_date
        == provider_thread_item.issuers[0].user_groups[0].slas[0].start_date
    )
    assert (
        sla.end_date == provider_thread_item.issuers[0].user_groups[0].slas[0].end_date
    )
    assert sla.project == provider_thread_item.provider_conf.projects[0].id


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_no_sla_match(provider_thread_item: ProviderThread):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    item = provider_thread_item.get_provider()

    assert provider_thread_item.error

    assert item is not None
    assert isinstance(item, ProviderCreateExtended)
    assert item.description == provider_thread_item.provider_conf.description
    assert item.name == provider_thread_item.provider_conf.name
    assert item.type == provider_thread_item.provider_conf.type
    assert item.status == ProviderStatus.LIMITED
    assert item.is_public == provider_thread_item.provider_conf.is_public
    assert item.support_emails == provider_thread_item.provider_conf.support_emails
    assert len(item.regions) == 0
    assert len(item.projects) == 0
    assert len(item.identity_providers) == 0


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_no_issuer_and_auth_method_match(provider_thread_item: ProviderThread):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    item = provider_thread_item.get_provider()

    assert provider_thread_item.error

    assert item is not None
    assert isinstance(item, ProviderCreateExtended)
    assert item.description == provider_thread_item.provider_conf.description
    assert item.name == provider_thread_item.provider_conf.name
    assert item.type == provider_thread_item.provider_conf.type
    assert item.status == ProviderStatus.LIMITED
    assert item.is_public == provider_thread_item.provider_conf.is_public
    assert item.support_emails == provider_thread_item.provider_conf.support_emails
    assert len(item.regions) == 0
    assert len(item.projects) == 0
    assert len(item.identity_providers) == 0


@patch("src.providers.core.ConnectionThread.__init__")
@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("error", cases=CaseThreadConnError)
def test_get_error_from_thread_connection(
    mock_conn_thread_init: Mock,
    provider_thread_item: ProviderThread,
    error: AssertionError | NotImplementedError | OpenstackProviderException,
):
    """Provider is Active or it has one project matching the SLA in the issuer."""
    provider_thread_item.provider_conf.projects[0].sla = (
        provider_thread_item.issuers[0].user_groups[0].slas[0].doc_uuid
    )
    provider_thread_item.provider_conf.identity_providers[
        0
    ].endpoint = provider_thread_item.issuers[0].endpoint
    mock_conn_thread_init.side_effect = error

    item = provider_thread_item.get_provider()

    assert item is not None
    assert isinstance(item, ProviderCreateExtended)
    assert item.description == provider_thread_item.provider_conf.description
    assert item.name == provider_thread_item.provider_conf.name
    assert item.type == provider_thread_item.provider_conf.type
    assert item.status == ProviderStatus.LIMITED
    assert item.is_public == provider_thread_item.provider_conf.is_public
    assert item.support_emails == provider_thread_item.provider_conf.support_emails
    assert len(item.regions) == 0
    assert len(item.projects) == 0
    assert len(item.identity_providers) == 0
