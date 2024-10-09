from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from openstack.network.v2.network import Network
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from src.providers.openstack import get_networks


class CaseTagList:
    @case(tags=["empty"])
    def case_empty_tag_list(self) -> list:
        return []

    @case(tags=["empty"])
    def case_no_list(self) -> None:
        return None

    @case(tags=["full"])
    def case_list(self) -> list[str]:
        return ["one"]


class CaseDefaultNet:
    @parametrize(default_net=["private", "public"])
    def case_default_attr(self, default_net: str) -> str:
        return default_net


def filter_networks(network: Network, tags: list[str] | None) -> bool:
    valid_tag = tags is None or len(tags) == 0
    if not valid_tag:
        valid_tag = len(set(network.tags).intersection(set(tags))) > 0
    return network.status == "active" and valid_tag


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=CaseTagList)
def test_retrieve_networks(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_network: Network,
    tags: list[str] | None,
) -> None:
    """Successful retrieval of a Network.

    Retrieve only active networks and with the tags contained in the target tags list.
    If the target tags list is empty or None, all active networks are valid ones.

    Networks retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    networks = list(filter(lambda x: filter_networks(x, tags), [openstack_network]))
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_network.project_id
    )
    data = get_networks(mock_conn, tags=tags)

    assert len(data) == len(networks)
    if len(data) > 0:
        item = data[0]
        if openstack_network.description:
            assert item.description == openstack_network.description
        else:
            assert item.description == ""
        assert item.uuid == openstack_network.id
        assert item.name == openstack_network.name
        assert item.is_shared == openstack_network.is_shared
        assert item.is_router_external == openstack_network.is_router_external
        assert item.is_default == bool(openstack_network.is_default)
        assert item.mtu == openstack_network.mtu
        assert not item.proxy_host
        assert not item.proxy_user
        assert item.tags == openstack_network.tags
        if item.is_shared:
            assert not item.project
        else:
            assert item.project
            assert item.project == openstack_network.project_id


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_not_owned_private_net(
    mock_conn: Mock, mock_network: Mock, openstack_network_base: Network
) -> None:
    """Networks owned by another project are not returned."""
    networks = [openstack_network_base]
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    data = get_networks(mock_conn)
    assert len(data) == 0


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_networks_with_proxy(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_network_base: Network,
    net_proxy: PrivateNetProxy,
) -> None:
    """Test retrieving networks with proxy ip and user.

    The network does not have proxy ip and user. This function attaches them to the
    network.
    """
    networks = [openstack_network_base]
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_network_base.project_id
    )
    data = get_networks(mock_conn, proxy=net_proxy)

    assert len(data) == len(networks)
    assert data[0].proxy_host == str(net_proxy.host)
    assert data[0].proxy_user == net_proxy.user


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("default_net", cases=CaseDefaultNet)
def test_retrieve_networks_with_default_net(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_default_network: Network,
    default_net: str,
) -> None:
    """Test how the is_default attribute in NetworkCreateExtended is built."""
    default_private_net = None
    default_public_net = None
    if default_net == "private":
        default_private_net = openstack_default_network.name
    if default_net == "public":
        default_public_net = openstack_default_network.name

    networks = [openstack_default_network]
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_default_network.project_id
    )
    data = get_networks(
        mock_conn,
        default_private_net=default_private_net,
        default_public_net=default_public_net,
    )

    assert len(data) == len(networks)
    if len(data) > 0:
        item = data[0]
        public_default_net_match_shared_net = (
            openstack_default_network.is_shared
            and default_public_net == openstack_default_network.name
        )
        private_default_net_match_not_shared_net = (
            not openstack_default_network.is_shared
            and default_private_net == openstack_default_network.name
        )
        net_marked_as_default = openstack_default_network.is_default
        assert item.is_default == (
            public_default_net_match_shared_net
            or private_default_net_match_not_shared_net
            or net_marked_as_default
        )
