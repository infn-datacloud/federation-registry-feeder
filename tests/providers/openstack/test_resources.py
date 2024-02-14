from typing import Tuple, Union
from unittest.mock import Mock, patch

from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    NetworkServiceCreateExtended,
    ProjectCreate,
)
from fed_reg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    NetworkServiceName,
)
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.connection import ConnectFailure
from keystoneauth1.exceptions.http import NotFound, Unauthorized
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Openstack, Project
from src.providers.openstack import get_data_from_openstack
from tests.schemas.utils import random_lower_string


class CaseConnException:
    def case_connect_failure(self) -> ConnectFailure:
        """The connection raises a ConnectFailure exception.

        Happens when the auth_url is invalid or during a timeout.
        """
        return ConnectFailure()

    def case_unauthorized(self) -> Unauthorized:
        """The connection raises an Unauthorized exception.

        Happens when the token expires, the protocol is wrong or the project_id is
        invalid.
        """
        return Unauthorized()

    def case_no_matching_plugin(self) -> NoMatchingPlugin:
        """The connection raises an NoMatchingPlugin exception.

        Happens when the auth method is not a valid one.
        """
        return NoMatchingPlugin(random_lower_string())

    def case_idp_not_found(self) -> NotFound:
        """The connection raises an NotFound exception.

        Happens when the identity provider url is wrong.
        """
        return NotFound()


class CaseFailPoint:
    @parametrize(call=["project", "block_storage", "compute", "network"])
    def case_lost_connection(self, call: str) -> str:
        return call


class CaseAbsentService:
    @parametrize(service=["block_storage", "compute", "network"])
    def case_absent(self, service: str) -> str:
        return service


@patch("src.providers.openstack.get_network_service")
@patch("src.providers.openstack.get_compute_service")
@patch("src.providers.openstack.get_block_storage_service")
@patch("src.providers.openstack.get_project")
@parametrize_with_cases("exception", cases=CaseConnException)
@parametrize_with_cases("fail_point", cases=CaseFailPoint)
def test_connection_error(
    mock_project: Mock,
    mock_block_storage_service: Mock,
    mock_compute_service: Mock,
    mock_network_service: Mock,
    configurations: Tuple[IdentityProviderCreateExtended, Openstack, Project],
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    fail_point: str,
    exception: Union[ConnectFailure, Unauthorized, NoMatchingPlugin, NotFound],
) -> None:
    """Test no initial connection or connection loss during procedure"""
    block_storage_service_create.name = BlockStorageServiceName.OPENSTACK_CINDER
    compute_service_create.name = ComputeServiceName.OPENSTACK_NOVA
    network_service_create.name = NetworkServiceName.OPENSTACK_NEUTRON

    mock_project.return_value = project_create
    mock_block_storage_service.return_value = block_storage_service_create
    mock_compute_service.return_value = compute_service_create
    mock_network_service.return_value = network_service_create

    if fail_point == "project":
        mock_project.side_effect = exception
    elif fail_point == "block_storage":
        mock_block_storage_service.side_effect = exception
    elif fail_point == "compute":
        mock_compute_service.side_effect = exception
    elif fail_point == "network":
        mock_network_service.side_effect = exception

    (issuer, provider_conf, project_conf) = configurations
    region_name = random_lower_string()
    token = random_lower_string()
    resp = get_data_from_openstack(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=issuer,
        region_name=region_name,
        token=token,
    )
    assert not resp
    if fail_point == "project":
        mock_project.assert_called()
        mock_block_storage_service.assert_not_called()
        mock_compute_service.assert_not_called()
        mock_network_service.assert_not_called()
    elif fail_point == "block_storage":
        mock_project.assert_called()
        mock_block_storage_service.assert_called()
        mock_compute_service.assert_not_called()
        mock_network_service.assert_not_called()
    elif fail_point == "compute":
        mock_project.assert_called()
        mock_block_storage_service.assert_called()
        mock_compute_service.assert_called()
        mock_network_service.assert_not_called()
    elif fail_point == "network":
        mock_project.assert_called()
        mock_block_storage_service.assert_called()
        mock_compute_service.assert_called()
        mock_network_service.assert_called()


@patch("src.providers.openstack.get_network_service")
@patch("src.providers.openstack.get_compute_service")
@patch("src.providers.openstack.get_block_storage_service")
@patch("src.providers.openstack.get_project")
@parametrize_with_cases("absent", cases=CaseAbsentService)
def test_retrieve_resources(
    mock_project: Mock,
    mock_block_storage_service: Mock,
    mock_compute_service: Mock,
    mock_network_service: Mock,
    configurations: Tuple[IdentityProviderCreateExtended, Openstack, Project],
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    absent: str,
) -> None:
    """One of the services does not exist on the specified region."""
    (issuer, provider_conf, project_conf) = configurations
    region_name = random_lower_string()
    token = random_lower_string()

    project_create.uuid = project_conf.id
    block_storage_service_create.name = BlockStorageServiceName.OPENSTACK_CINDER
    compute_service_create.name = ComputeServiceName.OPENSTACK_NOVA
    network_service_create.name = NetworkServiceName.OPENSTACK_NEUTRON

    mock_project.return_value = project_create
    mock_block_storage_service.return_value = (
        None if absent == "block_storage" else block_storage_service_create
    )
    mock_compute_service.return_value = (
        None if absent == "compute" else compute_service_create
    )
    mock_network_service.return_value = (
        None if absent == "network" else network_service_create
    )

    resp = get_data_from_openstack(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=issuer,
        region_name=region_name,
        token=token,
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
    if absent == "block_storage":
        assert not block_storage_service
    else:
        assert block_storage_service
    assert not compute_service if absent == "compute" else compute_service
    assert not network_service if absent == "network" else network_service
    mock_project.assert_called()
    mock_block_storage_service.assert_called()
    mock_compute_service.assert_called()
    mock_network_service.assert_called()
