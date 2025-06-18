from unittest.mock import Mock, PropertyMock, patch

from fedreg.v1.quota.enum import QuotaType
from openstack.network.v2.quota import QuotaDetails

from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import openstack_network_quotas_dict


@patch("src.providers.openstack.Connection")
def test_retrieve_network_quotas(
    mock_conn: Mock, openstack_item: OpenstackData
) -> None:
    """Retrieve a network quota."""
    d = {}
    limit_dict = openstack_network_quotas_dict()
    usage_dict = openstack_network_quotas_dict()
    for k in limit_dict.keys():
        d[k] = {"limit": limit_dict[k], "used": usage_dict[k]}
    quotaset = QuotaDetails(**d)
    mock_conn.network.get_quota.return_value = quotaset
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data_limit, data_usage = openstack_item.get_network_quotas()
    assert data_limit.type == QuotaType.NETWORK.value
    assert data_usage.type == QuotaType.NETWORK.value
    assert not data_limit.per_user
    assert not data_usage.per_user
    assert data_limit.ports == quotaset.get("ports").get("limit")
    assert data_usage.ports == quotaset.get("ports").get("used")
    assert data_limit.networks == quotaset.get("networks").get("limit")
    assert data_usage.networks == quotaset.get("networks").get("used")
    assert data_limit.public_ips == quotaset.get("floating_ips").get("limit")
    assert data_usage.public_ips == quotaset.get("floating_ips").get("used")
    assert data_limit.security_groups == quotaset.get("security_groups").get("limit")
    assert data_usage.security_groups == quotaset.get("security_groups").get("used")
    assert data_limit.security_group_rules == quotaset.get("security_group_rules").get(
        "limit"
    )
    assert data_usage.security_group_rules == quotaset.get("security_group_rules").get(
        "used"
    )
    assert data_limit.project == openstack_item.project_conf.id
    assert data_usage.project == openstack_item.project_conf.id
