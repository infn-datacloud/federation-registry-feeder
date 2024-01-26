from typing import Tuple
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.auth_method.schemas import AuthMethodBase
from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    NetworkServiceCreateExtended,
    ProjectCreate,
)
from app.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    NetworkServiceName,
)
from keystoneauth1.exceptions.connection import ConnectFailure
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import Openstack, Project, TrustedIDP
from src.providers.openstack import get_provider_resources
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@case(tags=["connection"])
@parametrize(item=["connection", "project", "block_storage", "compute", "network"])
def case_connection(item: str) -> str:
    return item


@case(tags=["item"])
@parametrize(item=["block_storage", "compute", "network"])
def case_absent_item(item: str) -> str:
    return item


@pytest.fixture
def configurations() -> Tuple[Openstack, Issuer, Project, str]:
    project_id = uuid4()
    start_date, end_date = random_start_end_dates()
    sla = SLA(
        doc_uuid=uuid4(),
        start_date=start_date,
        end_date=end_date,
        projects=[project_id],
    )
    user_group = UserGroup(name=random_lower_string(), slas=[sla])
    relationship = AuthMethodBase(
        idp_name=random_lower_string(), protocol=random_lower_string()
    )
    issuer = Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        relationship=relationship,
        user_groups=[user_group],
    )
    trusted_idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=relationship.idp_name,
        protocol=relationship.protocol,
    )
    project = Project(id=project_id, sla=sla.doc_uuid)
    provider_conf = Openstack(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[trusted_idp],
        projects=[project],
    )
    region_name = random_lower_string()
    return provider_conf, issuer, project, region_name


@patch("src.providers.openstack.get_network_service")
@patch("src.providers.openstack.get_compute_service")
@patch("src.providers.openstack.get_block_storage_service")
@patch("src.providers.openstack.get_project")
@patch("src.providers.openstack.connect_to_provider")
@parametrize_with_cases("fail_point", cases=".", has_tag="connection")
def test_no_connection(
    mock_conn,
    mock_project,
    mock_block_storage_service,
    mock_compute_service,
    mock_network_service,
    configurations: Tuple[Openstack, Issuer, Project, str],
    fail_point: str,
) -> None:
    """Test no initial connection and connection loss during procedure"""
    mock_project.return_value = ProjectCreate(uuid=uuid4(), name=random_lower_string())
    mock_block_storage_service.return_value = BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=BlockStorageServiceName.OPENSTACK_CINDER
    )
    mock_compute_service.return_value = ComputeServiceCreateExtended(
        endpoint=random_url(), name=ComputeServiceName.OPENSTACK_NOVA
    )
    mock_network_service.return_value = NetworkServiceCreateExtended(
        endpoint=random_url(), name=NetworkServiceName.OPENSTACK_NEUTRON
    )
    if fail_point == "connection":
        mock_conn.return_value = None
    elif fail_point == "project":
        mock_project.side_effect = ConnectFailure()
    elif fail_point == "block_storage":
        mock_block_storage_service.side_effect = ConnectFailure()
    elif fail_point == "compute":
        mock_compute_service.side_effect = ConnectFailure()
    elif fail_point == "network":
        mock_network_service.side_effect = ConnectFailure()

    (provider_conf, issuer, project_conf, region_name) = configurations
    resp = get_provider_resources(
        provider_conf=provider_conf,
        project_conf=project_conf,
        idp=issuer,
        region_name=region_name,
    )
    assert not resp


@patch("src.providers.openstack.get_network_service")
@patch("src.providers.openstack.get_compute_service")
@patch("src.providers.openstack.get_block_storage_service")
@patch("src.providers.openstack.get_project")
@parametrize_with_cases("absent", cases=".", has_tag="item")
def test_retrieve_resources(
    mock_project,
    mock_block_storage_service,
    mock_compute_service,
    mock_network_service,
    configurations: Tuple[Openstack, Issuer, Project, str],
    absent: str,
) -> None:
    (provider_conf, issuer, project_conf, region_name) = configurations
    mock_project.return_value = ProjectCreate(
        uuid=project_conf.id, name=random_lower_string()
    )
    mock_block_storage_service.return_value = BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=BlockStorageServiceName.OPENSTACK_CINDER
    )
    mock_compute_service.return_value = ComputeServiceCreateExtended(
        endpoint=random_url(), name=ComputeServiceName.OPENSTACK_NOVA
    )
    mock_network_service.return_value = NetworkServiceCreateExtended(
        endpoint=random_url(), name=NetworkServiceName.OPENSTACK_NEUTRON
    )
    if absent == "block_storage":
        mock_block_storage_service.return_value = None
    elif absent == "compute":
        mock_compute_service.return_value = None
    elif absent == "network":
        mock_network_service.return_value = None
    resp = get_provider_resources(
        provider_conf=provider_conf,
        project_conf=project_conf,
        idp=issuer,
        region_name=region_name,
    )
    assert resp

    (
        proj,
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    ) = resp
    assert proj
    assert identity_service
    assert (
        not block_storage_service
        if absent == "block_storage"
        else block_storage_service
    )
    assert not compute_service if absent == "compute" else compute_service
    assert not network_service if absent == "network" else network_service
