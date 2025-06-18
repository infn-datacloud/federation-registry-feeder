from unittest.mock import Mock, PropertyMock, patch

from fedreg.v1.quota.enum import QuotaType
from openstack.compute.v2.quota_set import QuotaSet

from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import openstack_compute_quotas_dict


@patch("src.providers.openstack.Connection")
def test_retrieve_compute_quotas(
    mock_conn: Mock, openstack_item: OpenstackData
) -> None:
    """Retrieve a compute quota."""
    quotaset = QuotaSet(
        **openstack_compute_quotas_dict(), usage=openstack_compute_quotas_dict()
    )
    mock_conn.compute.get_quota_set.return_value = quotaset
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data_limit, data_usage = openstack_item.get_compute_quotas()
    assert data_limit.type == QuotaType.COMPUTE.value
    assert data_usage.type == QuotaType.COMPUTE.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.cores == quotaset.get("cores")
    assert data_usage.cores == quotaset.get("usage").get("cores")
    assert data_limit.instances == quotaset.get("instances")
    assert data_usage.instances == quotaset.get("usage").get("instances")
    assert data_limit.ram == quotaset.get("ram")
    assert data_usage.ram == quotaset.get("usage").get("ram")
    assert data_limit.project == openstack_item.project_conf.id
    assert data_usage.project == openstack_item.project_conf.id
