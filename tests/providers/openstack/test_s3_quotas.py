from unittest.mock import Mock, PropertyMock, patch

from fedreg.quota.enum import QuotaType

from src.providers.openstack import OpenstackData


@patch("src.providers.openstack.Connection")
def test_retrieve_s3_quotas(mock_conn: Mock, openstack_item: OpenstackData) -> None:
    """Retrieve a object_store quota."""
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data_limit, data_usage = openstack_item.get_s3_quotas()
    assert data_limit.type == QuotaType.OBJECT_STORE.value
    assert data_usage.type == QuotaType.OBJECT_STORE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.bytes == -1
    assert data_usage.bytes == -1
    assert data_limit.containers == 1000
    assert data_usage.containers == 1000
    assert data_limit.objects == -1
    assert data_usage.objects == -1
    assert data_limit.project == openstack_item.project_conf.id
    assert data_usage.project == openstack_item.project_conf.id
