from random import getrandbits, randint
from typing import Any, Dict, List, Optional
from unittest.mock import patch
from uuid import uuid4

import pytest
from openstack.network.v2.network import Network
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from src.providers.openstack import get_networks
from tests.providers.openstack.utils import random_network_status
from tests.schemas.utils import random_ip, random_lower_string


@case(tags=["is_shared"])
@parametrize(is_shared=[True, False])
def case_is_shared(is_shared: bool) -> bool:
    return is_shared


@case(tags=["tags"])
@parametrize(tags=range(4))
def case_tags(tags: int) -> List[str]:
    if tags == 0:
        return ["one"]
    if tags == 1:
        return ["two"]
    if tags == 2:
        return ["one", "two"]
    if tags == 3:
        return ["one-two"]


@case(tags=["no_tags"])
@parametrize(empty_list=[True, False])
def case_empty_tag_list(empty_list: bool) -> Optional[List]:
    return [] if empty_list else None


@case(tags=["is_default"])
@parametrize(default_attr=["private", "public", "network"])
def case_default_attr(default_attr: bool) -> bool:
    return default_attr


def network_data() -> Dict[str, Any]:
    return {
        "id": uuid4().hex,
        "description": random_lower_string(),
        "name": random_lower_string(),
        "status": "active",
        "project_id": uuid4().hex,
        "is_default": False,
        "is_router_external": getrandbits(1),
        "is_shared": getrandbits(1),
        "mtu": randint(1, 100),
    }


@pytest.fixture
def network_base() -> Network:
    return Network(**network_data())


@pytest.fixture
def network_disabled() -> Network:
    d = network_data()
    d["status"] = random_network_status(exclude=["active"])
    return Network(**d)


@pytest.fixture
@parametrize_with_cases("is_shared", cases=".", has_tag="is_shared")
def network_shared(is_shared: bool) -> Network:
    d = network_data()
    d["is_shared"] = is_shared
    return Network(**d)


@pytest.fixture
@parametrize_with_cases("tags", cases=".", has_tag="tags")
def network_with_tags(tags: List[str]) -> Network:
    d = network_data()
    d["tags"] = tags
    return Network(**d)


@pytest.fixture
@parametrize(i=[network_disabled, network_shared])
def network(i: Network) -> Network:
    return i


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=".", has_tag="no_tags")
def test_retrieve_networks(
    mock_conn, mock_network, network: Network, tags: Optional[List]
) -> None:
    networks = list(filter(lambda x: x.status == "active", [network]))
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    data = get_networks(mock_conn, tags=tags)

    assert len(data) == len(networks)
    if len(data) > 0:
        item = data[0]
        assert item.description == network.description
        assert item.uuid == network.id
        assert item.name == network.name
        assert item.is_shared == network.is_shared
        assert item.is_router_external == network.is_router_external
        assert item.is_default == network.is_default
        assert item.mtu == network.mtu
        assert not item.proxy_ip
        assert not item.proxy_user
        assert item.tags == network.tags
        if item.is_shared:
            assert not item.project
        else:
            assert item.project
            assert item.project == network.project_id


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_networks_with_tags(
    mock_conn, mock_network, network_with_tags: Network
) -> None:
    target_tags = ["one"]
    networks = list(
        filter(
            lambda x: set(x.tags).intersection(set(target_tags)), [network_with_tags]
        )
    )
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    data = get_networks(mock_conn, tags=target_tags)
    assert len(data) == len(networks)


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_networks_with_proxy(
    mock_conn, mock_network, network_base: Network
) -> None:
    networks = [network_base]
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    proxy = PrivateNetProxy(ip=random_ip(), user=random_lower_string())
    data = get_networks(mock_conn, proxy=proxy)

    assert len(data) == len(networks)
    if len(data) > 0:
        item = data[0]
        assert item.proxy_ip == str(proxy.ip)
        assert item.proxy_user == proxy.user


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("default_attr", cases=".", has_tag="is_default")
def test_retrieve_networks_with_default_net(
    mock_conn, mock_network, network_shared: Network, default_attr: str
) -> None:
    default_private_net = network_shared.name if default_attr == "private" else None
    default_public_net = network_shared.name if default_attr == "public" else None
    network_shared.is_default = default_attr == "network"

    networks = [network_shared]
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    data = get_networks(
        mock_conn,
        default_private_net=default_private_net,
        default_public_net=default_public_net,
    )

    assert len(data) == len(networks)
    if len(data) > 0:
        item = data[0]
        assert item.is_default == (
            (network_shared.is_shared and default_public_net == network_shared.name)
            or (
                not network_shared.is_shared
                and default_private_net == network_shared.name
            )
            or network_shared.is_default
        )
