import os
from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    BlockStorageServiceCreateExtended,
)
from fed_reg.service.enum import BlockStorageServiceName, ServiceType
from keystoneauth1.exceptions.catalog import EndpointNotFound
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits
from src.providers.openstack import OpenstackData
from tests.schemas.utils import random_url


class CaseEndpointResp:
    def case_raise_exc(self) -> EndpointNotFound:
        return EndpointNotFound()

    def case_none(self) -> None:
        return None


class CaseUserQuotaPresence:
    def case_present(self) -> Literal[True]:
        return True

    def case_absent(self) -> Literal[False]:
        return False


@parametrize_with_cases("resp", cases=CaseEndpointResp)
@patch("src.providers.openstack.Connection")
def test_no_block_storage_service(
    mock_conn: Mock,
    resp: EndpointNotFound | None,
    openstack_item: OpenstackData,
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    with patch("src.providers.openstack.Connection.block_storage") as mock_srv:
        if resp:
            mock_srv.get_endpoint.side_effect = resp
        else:
            mock_srv.get_endpoint.return_value = resp
    mock_conn.block_storage = mock_srv
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    assert not openstack_item.get_block_storage_service()

    mock_srv.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_block_storage_quotas")
@patch("src.providers.openstack.Connection.block_storage")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_block_storage_service_with_quotas(
    mock_conn: Mock,
    mock_block_storage: Mock,
    mock_block_storage_quotas: Mock,
    user_quota: bool,
    openstack_item: OpenstackData,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = Limits(
        **{"block_storage": {"per_user": True}} if user_quota else {}
    )
    openstack_item.project_conf.per_user_limits = per_user_limits
    endpoint = random_url()
    mock_block_storage_quotas.return_value = (
        BlockStorageQuotaCreateExtended(project=openstack_item.project_conf.id),
        BlockStorageQuotaCreateExtended(
            project=openstack_item.project_conf.id, usage=True
        ),
    )
    mock_block_storage.get_endpoint.return_value = os.path.join(endpoint, uuid4().hex)
    mock_conn.block_storage = mock_block_storage
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    openstack_item.conn = mock_conn

    item = openstack_item.get_block_storage_service()
    assert isinstance(item, BlockStorageServiceCreateExtended)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.BLOCK_STORAGE.value
    assert item.name == BlockStorageServiceName.OPENSTACK_CINDER.value
    if user_quota:
        assert len(item.quotas) == 3
        assert item.quotas[2].per_user
    else:
        assert len(item.quotas) == 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
