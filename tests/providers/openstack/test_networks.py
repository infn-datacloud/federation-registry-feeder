from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fedreg.provider.schemas_extended import (
    PrivateNetworkCreateExtended,
    SharedNetworkCreate,
)
from openstack.network.v2.network import Network
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import (
    filter_item_by_tags,
    openstack_network_dict,
    random_network_status,
)
from tests.schemas.utils import network_dict, private_net_proxy_dict
from tests.utils import random_lower_string


class CaseTaglist:
    @case(tags="empty")
    def case_empty_tag_list(self) -> list:
        return []

    @case(tags="empty")
    def case_no_list(self) -> None:
        return None

    @case(tags="not-empty")
    def case_one_item(self) -> list[str]:
        return ["one"]

    @case(tags="not-empty")
    def case_two_items(self) -> list[str]:
        return ["one", "two"]


class CaseDefaultNet:
    @parametrize(default_net=["default_private_net", "default_public_net"])
    def case_default_attr(self, default_net: str) -> str:
        return default_net


class CaseNetwork:
    @parametrize(is_router_external=(True, False))
    def case_private_network(
        self, is_router_external: bool
    ) -> PrivateNetworkCreateExtended:
        """Fixture with network."""
        d = network_dict()
        return PrivateNetworkCreateExtended(
            **d, is_router_external=is_router_external, projects=[uuid4()]
        )

    @parametrize(is_router_external=(True, False))
    def case_shared_network(self, is_router_external: bool) -> SharedNetworkCreate:
        """Fixture with network."""
        d = network_dict()
        return SharedNetworkCreate(**d, is_router_external=is_router_external)


class CaseOpenstackNetwork:
    @case(tags=("base", "private"))
    def case_network_base(self) -> Network:
        """Fixture with network."""
        return Network(**openstack_network_dict())

    @case(tags=("base", "public"))
    def case_network_shared(self) -> Network:
        """Fixture with shared network."""
        d = openstack_network_dict()
        d["is_shared"] = True
        return Network(**d)

    @case(tags="public")
    def case_network_disabled(self) -> Network:
        """Fixture with disabled network."""
        d = openstack_network_dict()
        d["status"] = random_network_status(exclude=["active"])
        return Network(**d)

    @case(tags="public")
    def case_network_with_desc(self) -> Network:
        """Fixture with network with specified description."""
        d = openstack_network_dict()
        d["description"] = random_lower_string()
        return Network(**d)

    @case(tags="public")
    @parametrize(tags=(["one"], ["two"], ["one-two"], ["one", "two"]))
    def case_network_with_tags(self, tags: list[str]) -> Network:
        """Fixture with network with specified tags."""
        d = openstack_network_dict()
        d["tags"] = tags
        return Network(**d)


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("openstack_network", cases=CaseOpenstackNetwork)
@parametrize_with_cases("tags", cases=CaseTaglist, has_tag="empty")
def test_retrieve_networks(
    mock_conn: Mock,
    openstack_network: Network,
    openstack_item: OpenstackData,
    tags: list[str] | None,
) -> None:
    """Successful retrieval of a Network.

    Retrieve only active networks and with the tags contained in the target tags list.
    If the target tags list is empty or None, all active networks are valid ones.

    Networks retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    openstack_network.project_id = openstack_item.project_conf.id
    networks = [openstack_network]
    mock_conn.network.networks.return_value = networks
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_networks(tags=tags)

    assert len(data) == len(networks)
    if len(data) > 0:
        item = data[0]
        assert isinstance(item, (PrivateNetworkCreateExtended, SharedNetworkCreate))
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
        if isinstance(item, SharedNetworkCreate):
            assert not hasattr(item, "projects")
        else:
            assert item.projects
            assert openstack_network.project_id in item.projects


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=CaseTaglist, has_tag="not-empty")
def test_tags_filter(
    mock_conn: Mock,
    openstack_item: OpenstackData,
    tags: list[str],
) -> None:
    """Successful retrieval of an Image.

    Retrieve only active networks and with the tags contained in the target tags list.
    If the target tags list is empty or None, all active networks are valid ones.

    Images retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    openstack_network1 = Network(**openstack_network_dict())
    openstack_network1.is_shared = True
    openstack_network1.tags = ["one", "two"]
    openstack_network2 = Network(**openstack_network_dict())
    openstack_network2.is_shared = True
    openstack_network2.tags = ["one-two"]

    networks = list(
        filter(
            lambda x: filter_item_by_tags(x, tags) and x.status == "active",
            [openstack_network1, openstack_network2],
        )
    )
    mock_conn.network.networks.return_value = networks
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_networks(tags=tags)
    assert len(data) == 1
    item = data[0]
    assert len(set(tags).intersection(set(item.tags)))


@patch("src.providers.openstack.Connection")
@parametrize_with_cases(
    "openstack_network", cases=CaseOpenstackNetwork, has_tag="private"
)
def test_not_owned_private_net(
    mock_conn: Mock,
    openstack_network: Network,
    openstack_item: OpenstackData,
) -> None:
    """Networks owned by another project are returned.

    These networks are private and the current project is linked to that network.
    """
    networks = [openstack_network]
    mock_conn.network.networks.return_value = networks
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_networks()
    assert len(data) == 1
    assert isinstance(data[0], PrivateNetworkCreateExtended)
    assert len(data[0].projects) == 1
    assert data[0].projects[0] == openstack_item.project_conf.id


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("openstack_network", cases=CaseOpenstackNetwork, has_tag="base")
def test_retrieve_networks_with_proxy(
    mock_conn: Mock,
    openstack_network: Network,
    openstack_item: OpenstackData,
) -> None:
    """Test retrieving networks with proxy ip and user.

    The network does not have proxy ip and user. This function attaches them to the
    network.
    """
    net_proxy = PrivateNetProxy(**private_net_proxy_dict())
    openstack_network.project_id = openstack_item.project_conf.id
    mock_conn.network.networks.return_value = [openstack_network]
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_networks(proxy=net_proxy)
    assert len(data) == 1
    assert data[0].proxy_host == str(net_proxy.host)
    assert data[0].proxy_user == net_proxy.user


@parametrize_with_cases("network", cases=CaseNetwork)
def test_is_default_network(
    network: PrivateNetworkCreateExtended | SharedNetworkCreate,
    openstack_item: OpenstackData,
):
    assert not openstack_item.is_default_network(network=network)

    if network.is_router_external:
        args = {"default_private_net": network.name}
    else:
        args = {"default_public_net": network.name}
    assert not openstack_item.is_default_network(network=network, **args)

    if network.is_router_external:
        args = {"default_public_net": network.name}
    else:
        args = {"default_private_net": network.name}
    assert openstack_item.is_default_network(network=network, **args)

    assert openstack_item.is_default_network(network=network, is_unique=True)
    if network.is_router_external:
        args = {"default_private_net": network.name, "is_unique": True}
    else:
        args = {"default_public_net": network.name, "is_unique": True}
    assert openstack_item.is_default_network(network=network, **args)

    network.is_default = True
    assert openstack_item.is_default_network(network=network)
