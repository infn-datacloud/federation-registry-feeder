from random import randint
from unittest.mock import Mock, PropertyMock, patch

from fedreg.v1.quota.enum import QuotaType
from openstack.object_store.v1.info import Info
from requests import Response

from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import openstack_object_store_headers


@patch("src.providers.openstack.Connection")
def test_retrieve_object_store_quotas(
    mock_conn: Mock, openstack_item: OpenstackData
) -> None:
    """Retrieve a object_store quota."""
    resp = Response()
    resp.headers = openstack_object_store_headers()
    info = Info(swift={"container_listing_limit": randint(0, 100)})
    mock_conn.object_store.get.return_value = resp
    mock_conn.object_store.get_info.return_value = info
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data_limit, data_usage = openstack_item.get_object_store_quotas()
    assert data_limit.type == QuotaType.OBJECT_STORE.value
    assert data_usage.type == QuotaType.OBJECT_STORE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.bytes == resp.headers.get("X-Account-Meta-Quota-Bytes")
    assert data_usage.bytes == resp.headers.get("X-Account-Bytes-Used")
    assert data_limit.containers == info.swift.get("container_listing_limit")
    assert data_usage.containers == resp.headers.get("X-Account-Container-Count")
    assert data_limit.objects == -1
    assert data_usage.objects == resp.headers.get("X-Account-Object-Count")
    assert data_limit.project == openstack_item.project_conf.id
    assert data_usage.project == openstack_item.project_conf.id
