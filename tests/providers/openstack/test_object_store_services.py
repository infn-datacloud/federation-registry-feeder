import os
from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    ObjectStoreQuotaCreateExtended,
    ObjectStoreServiceCreateExtended,
)
from fed_reg.service.enum import ObjectStoreServiceName, ServiceType
from keystoneauth1.exceptions.catalog import EndpointNotFound
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits
from src.providers.openstack import OpenstackData
from tests.utils import random_url


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
def test_no_object_store_service(
    mock_conn: Mock, resp: EndpointNotFound | None, openstack_item: OpenstackData
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    if resp:
        mock_conn.object_store.get_endpoint.side_effect = resp
    else:
        mock_conn.object_store.get_endpoint.return_value = resp
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    openstack_item.conn = mock_conn

    assert not openstack_item.get_object_store_service()
    mock_conn.object_store.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_object_store_quotas")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_object_store_service_with_quotas(
    mock_conn: Mock,
    mock_object_store_quotas: Mock,
    user_quota: bool,
    openstack_item: OpenstackData,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = Limits(
        **{"object_store": {"per_user": True}} if user_quota else {}
    )
    openstack_item.project_conf.per_user_limits = per_user_limits
    mock_object_store_quotas.return_value = (
        ObjectStoreQuotaCreateExtended(project=openstack_item.project_conf.id),
        ObjectStoreQuotaCreateExtended(
            project=openstack_item.project_conf.id, usage=True
        ),
    )
    endpoint = random_url()
    mock_conn.object_store.get_endpoint.return_value = os.path.join(
        endpoint, openstack_item.project_conf.id
    )
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_object_store_service()
    assert isinstance(item, ObjectStoreServiceCreateExtended)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.OBJECT_STORE.value
    assert item.name == ObjectStoreServiceName.OPENSTACK_SWIFT.value
    if user_quota:
        assert len(item.quotas) == 3
        assert item.quotas[2].per_user
    else:
        assert len(item.quotas) == 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
