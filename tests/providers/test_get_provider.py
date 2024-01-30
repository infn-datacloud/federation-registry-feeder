from unittest.mock import patch

import pytest
from app.provider.enum import ProviderStatus, ProviderType
from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ProjectCreate,
)
from app.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
)
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Kubernetes, Openstack, Project
from src.providers.core import get_provider
from tests.schemas.utils import random_lower_string, random_url


@case(tags=["type"])
@parametrize(type=[ProviderType.OS, ProviderType.K8S])
def case_provider_type(type: ProviderType) -> ProviderType:
    return type


@case(tags=["status"])
@parametrize(status=[ProviderStatus.ACTIVE, ProviderStatus.MAINTENANCE])
def case_provider_status(status: ProviderStatus) -> ProviderStatus:
    return status


@parametrize_with_cases("provider_type", cases=".", has_tag="type")
@parametrize_with_cases("provider_status", cases=".", has_tag="status")
def test_retrieve_empty_provider(
    provider_type: ProviderType,
    provider_status: ProviderStatus,
    issuer: Issuer,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    if provider_type == ProviderType.OS:
        provider = openstack_provider
    elif provider_type == ProviderType.K8S:
        provider = kubernetes_provider

    provider.status = provider_status.value

    item = get_provider(provider_conf=provider, issuers=[issuer])
    assert item.description == provider.description
    assert item.name == provider.name
    assert item.type == provider.type
    assert item.status == provider.status
    assert item.is_public == provider.is_public
    assert item.support_emails == provider.support_emails
    assert len(item.regions) == 0
    assert len(item.projects) == 0
    assert len(item.identity_providers) == 0


@patch("src.providers.core.get_idp_project_and_region")
@parametrize_with_cases("provider_type", cases=".", has_tag="type")
def test_failed_retrieve_provider(
    mock_func,
    provider_type: ProviderType,
    issuer: Issuer,
    project: Project,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    mock_func.return_value = None

    if provider_type == ProviderType.OS:
        provider = openstack_provider
    elif provider_type == ProviderType.K8S:
        provider = kubernetes_provider

    provider.projects = [project]

    item = get_provider(provider_conf=provider, issuers=[issuer])
    assert item.description == provider.description
    assert item.name == provider.name
    assert item.type == provider.type
    assert item.status == provider.status
    assert item.is_public == provider.is_public
    assert item.support_emails == provider.support_emails
    assert len(item.regions) == 0
    assert len(item.projects) == 0
    assert len(item.identity_providers) == 0


@patch("src.providers.core.get_data_from_openstack")
@parametrize_with_cases("provider_type", cases=".", has_tag="type")
def test_retrieve_provider(
    mock_func,
    provider_type: ProviderType,
    issuer: Issuer,
    project: Project,
    auth_method: AuthMethod,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    if provider_type == ProviderType.OS:
        provider = openstack_provider
        mock_func.return_value = (
            ProjectCreate(uuid=project.id, name=random_lower_string()),
            BlockStorageServiceCreateExtended(
                endpoint=random_url(), name=BlockStorageServiceName.OPENSTACK_CINDER
            ),
            ComputeServiceCreateExtended(
                endpoint=random_url(), name=ComputeServiceName.OPENSTACK_NOVA
            ),
            IdentityServiceCreate(
                endpoint=random_url(), name=IdentityServiceName.OPENSTACK_KEYSTONE
            ),
            NetworkServiceCreateExtended(
                endpoint=random_url(), name=NetworkServiceName.OPENSTACK_NEUTRON
            ),
        )
    elif provider_type == ProviderType.K8S:
        provider = kubernetes_provider
        mock_func.return_value = (
            ProjectCreate(uuid=project.id, name=random_lower_string()),
            BlockStorageServiceCreateExtended(
                endpoint=random_url(), name=BlockStorageServiceName.OPENSTACK_CINDER
            ),
            ComputeServiceCreateExtended(
                endpoint=random_url(), name=ComputeServiceName.OPENSTACK_NOVA
            ),
            IdentityServiceCreate(
                endpoint=random_url(), name=IdentityServiceName.OPENSTACK_KEYSTONE
            ),
            NetworkServiceCreateExtended(
                endpoint=random_url(), name=NetworkServiceName.OPENSTACK_NEUTRON
            ),
        )
        pytest.skip("Not yet implemented.")

    project.sla = issuer.user_groups[0].slas[0].doc_uuid
    provider.projects = [project]
    auth_method.endpoint = issuer.endpoint
    provider.identity_providers.append(auth_method)

    item = get_provider(provider_conf=provider, issuers=[issuer])
    assert item.description == provider.description
    assert item.name == provider.name
    assert item.type == provider.type
    assert item.status == provider.status
    assert item.is_public == provider.is_public
    assert item.support_emails == provider.support_emails
    assert len(item.regions) == len(provider.regions)
    assert len(item.projects) == len(provider.projects)
    assert len(item.identity_providers) == len([issuer])
