from unittest.mock import Mock, patch

import pytest
from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
)
from fed_reg.service.enum import IdentityServiceName
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.connection import ConnectFailure, ConnectTimeout, SSLError
from keystoneauth1.exceptions.http import GatewayTimeout, NotFound, Unauthorized
from openstack.exceptions import ForbiddenException, HttpException
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.exceptions import ProviderException
from src.providers.openstack import OpenstackData
from tests.schemas.utils import random_lower_string


class CaseConnException:
    def case_connect_failure(self) -> ConnectFailure:
        """The connection raises a ConnectFailure exception.

        Happens when the auth_url is invalid or during a timeout.
        """
        return ConnectFailure()

    def case_connection_timeout(self) -> ConnectTimeout:
        """The connection raises a ConnectFailure exception.

        Happens when the auth_url is invalid or during a timeout.
        """
        return ConnectTimeout()

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

    def case_forbidden(self) -> ForbiddenException:
        """The connection raises an NotFound exception.

        Happens when the identity provider url is wrong.
        """
        return ForbiddenException()

    def case_ssl(self) -> SSLError:
        """The connection raises an NotFound exception.

        Happens when the identity provider url is wrong.
        """
        return SSLError()

    def case_gateway_timeout(self) -> GatewayTimeout:
        """The connection raises an NotFound exception.

        Happens when the identity provider url is wrong.
        """
        return GatewayTimeout()

    def case_http_exception(self) -> HttpException:
        """The connection raises an NotFound exception.

        Happens when the identity provider url is wrong.
        """
        return HttpException()


class CaseAbsentService:
    @parametrize(service=["block_storage", "compute", "network"])
    def case_absent(self, service: str) -> str:
        return service


@patch("src.providers.openstack.OpenstackData")
def test_retrieve_info(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    object_store_service_create: ObjectStoreServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
    caplog: pytest.FixtureRequest,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.return_value = project_create
    mock_openstack_data.get_block_storage_service.return_value = (
        block_storage_service_create
    )
    mock_openstack_data.get_compute_service.return_value = compute_service_create
    mock_openstack_data.get_network_service.return_value = network_service_create
    mock_openstack_data.get_object_store_service.return_value = (
        object_store_service_create
    )
    mock_openstack_data.get_s3_services.return_value = [s3_service_create]

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_called()
    mock_openstack_data.get_compute_service.assert_called()
    mock_openstack_data.get_network_service.assert_called()
    # mock_openstack_data.get_object_store_service.assert_called()
    mock_openstack_data.get_s3_services.assert_called()

    assert openstack_item.identity_service is not None
    assert (
        openstack_item.identity_service.endpoint
        == openstack_item.provider_conf.auth_url
    )
    assert (
        openstack_item.identity_service.name == IdentityServiceName.OPENSTACK_KEYSTONE
    )
    assert openstack_item.project == project_create
    assert openstack_item.block_storage_service == block_storage_service_create
    assert openstack_item.compute_service == compute_service_create
    assert openstack_item.network_service == network_service_create
    assert openstack_item.object_store_services == [
        # object_store_service_create,
        s3_service_create,
    ]


@patch("src.providers.openstack.OpenstackData")
def test_missing_services(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    project_create: ProjectCreate,
    caplog: pytest.FixtureRequest,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.return_value = project_create
    mock_openstack_data.get_block_storage_service.return_value = None
    mock_openstack_data.get_compute_service.return_value = None
    mock_openstack_data.get_network_service.return_value = None
    mock_openstack_data.get_object_store_service.return_value = None
    mock_openstack_data.get_s3_services.return_value = []

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_called()
    mock_openstack_data.get_compute_service.assert_called()
    mock_openstack_data.get_network_service.assert_called()
    # mock_openstack_data.get_object_store_service.assert_called()
    mock_openstack_data.get_s3_services.assert_called()

    assert openstack_item.identity_service is not None
    assert (
        openstack_item.identity_service.endpoint
        == openstack_item.provider_conf.auth_url
    )
    assert (
        openstack_item.identity_service.name == IdentityServiceName.OPENSTACK_KEYSTONE
    )
    assert openstack_item.project == project_create
    assert openstack_item.block_storage_service is None
    assert openstack_item.compute_service is None
    assert openstack_item.network_service is None
    assert len(openstack_item.object_store_services) == 0


@patch("src.providers.openstack.OpenstackData")
@parametrize_with_cases("exception", cases=CaseConnException)
def test_project_connection_error(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    object_store_service_create: ObjectStoreServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
    exception: ConnectFailure | Unauthorized | NoMatchingPlugin | NotFound,
    caplog: pytest.CaptureFixture,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.side_effect = exception
    mock_openstack_data.get_block_storage_service.return_value = (
        block_storage_service_create
    )
    mock_openstack_data.get_compute_service.return_value = compute_service_create
    mock_openstack_data.get_network_service.return_value = network_service_create
    mock_openstack_data.get_object_store_service.return_value = (
        object_store_service_create
    )
    mock_openstack_data.get_s3_services.return_value = [s3_service_create]

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    with pytest.raises(ProviderException):
        openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_not_called()
    mock_openstack_data.get_compute_service.assert_not_called()
    mock_openstack_data.get_network_service.assert_not_called()
    mock_openstack_data.get_object_store_service.assert_not_called()
    mock_openstack_data.get_s3_services.assert_not_called()

    assert openstack_item.error
    assert openstack_item.project is None
    assert openstack_item.block_storage_service is None
    assert openstack_item.compute_service is None
    assert openstack_item.network_service is None
    assert len(openstack_item.object_store_services) == 0

    assert caplog.text.strip("\n").endswith("Connection aborted")


@patch("src.providers.openstack.OpenstackData")
@parametrize_with_cases("exception", cases=CaseConnException)
def test_block_storage_connection_error(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    project_create: ProjectCreate,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    object_store_service_create: ObjectStoreServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
    exception: ConnectFailure | Unauthorized | NoMatchingPlugin | NotFound,
    caplog: pytest.CaptureFixture,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.return_value = project_create
    mock_openstack_data.get_block_storage_service.side_effect = exception
    mock_openstack_data.get_compute_service.return_value = compute_service_create
    mock_openstack_data.get_network_service.return_value = network_service_create
    mock_openstack_data.get_object_store_service.return_value = (
        object_store_service_create
    )
    mock_openstack_data.get_s3_services.return_value = [s3_service_create]

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    with pytest.raises(ProviderException):
        openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_called()
    mock_openstack_data.get_compute_service.assert_not_called()
    mock_openstack_data.get_network_service.assert_not_called()
    mock_openstack_data.get_object_store_service.assert_not_called()
    mock_openstack_data.get_s3_services.assert_not_called()

    assert openstack_item.error
    assert openstack_item.project == project_create
    assert openstack_item.block_storage_service is None
    assert openstack_item.compute_service is None
    assert openstack_item.network_service is None
    assert len(openstack_item.object_store_services) == 0

    assert caplog.text.strip("\n").endswith("Connection aborted")


@patch("src.providers.openstack.OpenstackData")
@parametrize_with_cases("exception", cases=CaseConnException)
def test_compute_connection_error(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    object_store_service_create: ObjectStoreServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
    exception: ConnectFailure | Unauthorized | NoMatchingPlugin | NotFound,
    caplog: pytest.CaptureFixture,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.return_value = project_create
    mock_openstack_data.get_block_storage_service.return_value = (
        block_storage_service_create
    )
    mock_openstack_data.get_compute_service.side_effect = exception
    mock_openstack_data.get_network_service.return_value = network_service_create
    mock_openstack_data.get_object_store_service.return_value = (
        object_store_service_create
    )
    mock_openstack_data.get_s3_services.return_value = [s3_service_create]

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    with pytest.raises(ProviderException):
        openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_called()
    mock_openstack_data.get_compute_service.assert_called()
    mock_openstack_data.get_network_service.assert_not_called()
    mock_openstack_data.get_object_store_service.assert_not_called()
    mock_openstack_data.get_s3_services.assert_not_called()

    assert openstack_item.error
    assert openstack_item.project == project_create
    assert openstack_item.block_storage_service == block_storage_service_create
    assert openstack_item.compute_service is None
    assert openstack_item.network_service is None
    assert len(openstack_item.object_store_services) == 0

    assert caplog.text.strip("\n").endswith("Connection aborted")


@patch("src.providers.openstack.OpenstackData")
@parametrize_with_cases("exception", cases=CaseConnException)
def test_network_connection_error(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    object_store_service_create: ObjectStoreServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
    exception: ConnectFailure | Unauthorized | NoMatchingPlugin | NotFound,
    caplog: pytest.CaptureFixture,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.return_value = project_create
    mock_openstack_data.get_block_storage_service.return_value = (
        block_storage_service_create
    )
    mock_openstack_data.get_compute_service.return_value = compute_service_create
    mock_openstack_data.get_network_service.side_effect = exception
    mock_openstack_data.get_object_store_service.return_value = (
        object_store_service_create
    )
    mock_openstack_data.get_s3_services.return_value = [s3_service_create]

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    with pytest.raises(ProviderException):
        openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_called()
    mock_openstack_data.get_compute_service.assert_called()
    mock_openstack_data.get_network_service.assert_called()
    mock_openstack_data.get_object_store_service.assert_not_called()
    mock_openstack_data.get_s3_services.assert_not_called()

    assert openstack_item.error
    assert openstack_item.project == project_create
    assert openstack_item.block_storage_service == block_storage_service_create
    assert openstack_item.compute_service == compute_service_create
    assert openstack_item.network_service is None
    assert len(openstack_item.object_store_services) == 0

    assert caplog.text.strip("\n").endswith("Connection aborted")


# @patch("src.providers.openstack.OpenstackData")
# @parametrize_with_cases("exception", cases=CaseConnException)
# def test_object_store_connection_error(
#     mock_openstack_data: Mock,
#     openstack_item: OpenstackData,
#     project_create: ProjectCreate,
#     block_storage_service_create: BlockStorageServiceCreateExtended,
#     compute_service_create: ComputeServiceCreateExtended,
#     network_service_create: NetworkServiceCreateExtended,
#     s3_service_create: ObjectStoreServiceCreateExtended,
#     exception: ConnectFailure | Unauthorized | NoMatchingPlugin | NotFound,
#     caplog: pytest.CaptureFixture,
# ) -> None:
#     """Test no initial connection or connection loss during procedure"""
#     mock_openstack_data.get_project.return_value = project_create
#     mock_openstack_data.get_block_storage_service.return_value = (
#         block_storage_service_create
#     )
#     mock_openstack_data.get_compute_service.return_value = compute_service_create
#     mock_openstack_data.get_network_service.return_value = network_service_create
#     mock_openstack_data.get_object_store_service.side_effect = exception
#     mock_openstack_data.get_s3_services.return_value = [s3_service_create]

#     openstack_item.get_project = mock_openstack_data.get_project
#     openstack_item.get_block_storage_service = (
#         mock_openstack_data.get_block_storage_service
#     )
#     openstack_item.get_compute_service = mock_openstack_data.get_compute_service
#     openstack_item.get_network_service = mock_openstack_data.get_network_service
#     openstack_item.get_object_store_service = (
#         mock_openstack_data.get_object_store_service
#     )
#     openstack_item.get_s3_services = mock_openstack_data.get_s3_services

#     with pytest.raises(ProviderException):
#         openstack_item.retrieve_info()

#     mock_openstack_data.get_project.assert_called()
#     mock_openstack_data.get_block_storage_service.assert_called()
#     mock_openstack_data.get_compute_service.assert_called()
#     mock_openstack_data.get_network_service.assert_called()
#     mock_openstack_data.get_object_store_service.assert_called()
#     mock_openstack_data.get_s3_services.assert_not_called()

# assert openstack_item.project == project_create
# assert openstack_item.block_storage_service == block_storage_service_create
# assert openstack_item.compute_service == compute_service_create
# assert openstack_item.network_service == network_service_create
# assert len(openstack_item.object_store_services) == 0

#     assert caplog.text.strip("\n").endswith("Connection aborted")


@patch("src.providers.openstack.OpenstackData")
@parametrize_with_cases("exception", cases=CaseConnException)
def test_s3_connection_error(
    mock_openstack_data: Mock,
    openstack_item: OpenstackData,
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    object_store_service_create: ObjectStoreServiceCreateExtended,
    exception: ConnectFailure | Unauthorized | NoMatchingPlugin | NotFound,
    caplog: pytest.CaptureFixture,
) -> None:
    """Test no initial connection or connection loss during procedure"""
    mock_openstack_data.get_project.return_value = project_create
    mock_openstack_data.get_block_storage_service.return_value = (
        block_storage_service_create
    )
    mock_openstack_data.get_compute_service.return_value = compute_service_create
    mock_openstack_data.get_network_service.return_value = network_service_create
    mock_openstack_data.get_object_store_service.return_value = (
        object_store_service_create
    )
    mock_openstack_data.get_s3_services.side_effect = exception

    openstack_item.get_project = mock_openstack_data.get_project
    openstack_item.get_block_storage_service = (
        mock_openstack_data.get_block_storage_service
    )
    openstack_item.get_compute_service = mock_openstack_data.get_compute_service
    openstack_item.get_network_service = mock_openstack_data.get_network_service
    openstack_item.get_object_store_service = (
        mock_openstack_data.get_object_store_service
    )
    openstack_item.get_s3_services = mock_openstack_data.get_s3_services

    with pytest.raises(ProviderException):
        openstack_item.retrieve_info()

    mock_openstack_data.get_project.assert_called()
    mock_openstack_data.get_block_storage_service.assert_called()
    mock_openstack_data.get_compute_service.assert_called()
    mock_openstack_data.get_network_service.assert_called()
    # mock_openstack_data.get_object_store_service.assert_called()
    mock_openstack_data.get_s3_services.assert_called()

    assert openstack_item.error
    assert openstack_item.project == project_create
    assert openstack_item.block_storage_service == block_storage_service_create
    assert openstack_item.compute_service == compute_service_create
    assert openstack_item.network_service == network_service_create
    assert len(openstack_item.object_store_services) == 0

    assert caplog.text.strip("\n").endswith("Connection aborted")
