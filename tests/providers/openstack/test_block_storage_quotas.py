from unittest.mock import Mock, PropertyMock, patch

from fed_reg.quota.enum import QuotaType
from openstack.block_storage.v3.quota_set import QuotaSet
from openstack.exceptions import ForbiddenException

from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import openstack_block_storage_quotas_dict


@patch("src.providers.openstack.Connection")
def test_retrieve_block_storage_quotas(
    mock_conn: Mock, openstack_item: OpenstackData
) -> None:
    """Retrieve a block storage quota."""
    quotaset = QuotaSet(
        **openstack_block_storage_quotas_dict(),
        usage=openstack_block_storage_quotas_dict(),
    )
    mock_conn.block_storage.get_quota_set.return_value = quotaset
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data_limit, data_usage = openstack_item.get_block_storage_quotas()
    assert data_limit.type == QuotaType.BLOCK_STORAGE.value
    assert data_usage.type == QuotaType.BLOCK_STORAGE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.gigabytes == quotaset.get("gigabytes")
    assert data_usage.gigabytes == quotaset.get("usage").get("gigabytes")
    assert data_limit.per_volume_gigabytes == quotaset.get("per_volume_gigabytes")
    assert data_usage.per_volume_gigabytes == quotaset.get("usage").get(
        "per_volume_gigabytes"
    )
    assert data_limit.volumes == quotaset.get("volumes")
    assert data_usage.volumes == quotaset.get("usage").get("volumes")
    assert data_limit.project == openstack_item.project_conf.id
    assert data_usage.project == openstack_item.project_conf.id


@patch("src.providers.openstack.Connection")
def test_catch_forbidden_when_reading_block_storage_quotas(
    mock_conn: Mock, openstack_item: OpenstackData
) -> None:
    """Retrieve a block storage quota."""
    mock_conn.block_storage.get_quota_set.side_effect = ForbiddenException()
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data_limit, data_usage = openstack_item.get_block_storage_quotas()
    assert data_limit.type == QuotaType.BLOCK_STORAGE.value
    assert data_usage.type == QuotaType.BLOCK_STORAGE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.gigabytes is None
    assert data_usage.gigabytes is None
    assert data_limit.per_volume_gigabytes is None
    assert data_usage.per_volume_gigabytes is None
    assert data_limit.volumes is None
    assert data_usage.volumes is None
    assert data_limit.project == openstack_item.project_conf.id
    assert data_usage.project == openstack_item.project_conf.id
    assert openstack_item.error
