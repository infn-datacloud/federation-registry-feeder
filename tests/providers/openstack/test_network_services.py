from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fedreg.provider.schemas_extended import (
    NetworkCreateExtended,
    NetworkQuotaCreateExtended,
    NetworkServiceCreateExtended,
)
from fedreg.service.enum import NetworkServiceName, ServiceType
from keystoneauth1.exceptions.catalog import EndpointNotFound
from pytest_cases import case, parametrize_with_cases

from src.models.provider import Limits, PrivateNetProxy
from src.providers.openstack import OpenstackData
from tests.schemas.utils import private_net_proxy_dict
from tests.utils import random_lower_string, random_url


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


class CaseResourceVisibility:
    @case(tags="default")
    def case_public(self) -> Literal["public"]:
        return "public"

    @case(tags="default")
    def case_private(self) -> Literal["private"]:
        return "private"

    def case_not_accessible(self) -> Literal["no-access"]:
        return "no-access"


class CaseTagList:
    def case_empty_list(self) -> list:
        return []

    def case_list(self) -> list[str]:
        return ["one"]


@parametrize_with_cases("resp", cases=CaseEndpointResp)
@patch("src.providers.openstack.Connection")
def test_no_network_service(
    mock_conn: Mock, resp: EndpointNotFound | None, openstack_item: OpenstackData
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    if resp:
        mock_conn.network.get_endpoint.side_effect = resp
    else:
        mock_conn.network.get_endpoint.return_value = resp
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    assert not openstack_item.get_network_service()
    if resp:
        assert openstack_item.error
    mock_conn.network.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_network_quotas")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_network_service_with_quotas(
    mock_conn: Mock,
    mock_network_quotas: Mock,
    user_quota: bool,
    openstack_item: OpenstackData,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = Limits(**{"network": {"per_user": True}} if user_quota else {})
    openstack_item.project_conf.per_user_limits = per_user_limits
    mock_network_quotas.return_value = (
        NetworkQuotaCreateExtended(project=openstack_item.project_conf.id),
        NetworkQuotaCreateExtended(project=openstack_item.project_conf.id, usage=True),
    )
    endpoint = random_url()
    mock_conn.network.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_network_service()
    assert isinstance(item, NetworkServiceCreateExtended)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.NETWORK.value
    assert item.name == NetworkServiceName.OPENSTACK_NEUTRON.value
    if user_quota:
        assert len(item.quotas) == 3
        assert item.quotas[2].per_user
    else:
        assert len(item.quotas) == 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
    assert len(item.networks) == 0


@parametrize_with_cases("visibility", cases=CaseResourceVisibility)
@patch("src.providers.openstack.OpenstackData.get_networks")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_service_with_networks(
    mock_conn: Mock,
    mock_networks: Mock,
    openstack_item: OpenstackData,
    visibility: str,
) -> None:
    """Check networks in the returned service."""
    if visibility == "public":
        mock_networks.return_value = [
            NetworkCreateExtended(uuid=uuid4(), name=random_lower_string())
        ]
    elif visibility == "private":
        mock_networks.return_value = [
            NetworkCreateExtended(
                uuid=uuid4(),
                name=random_lower_string(),
                is_shared=False,
                project=openstack_item.project_conf.id,
            )
        ]
    elif visibility == "no-access":
        mock_networks.return_value = []
    endpoint = random_url()
    mock_conn.network.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_network_service()
    if visibility == "no-access":
        assert len(item.networks) == 0
    else:
        assert len(item.networks) == 1


@parametrize_with_cases("tags", cases=CaseTagList)
@patch("src.providers.openstack.OpenstackData.get_networks")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_service_networks_tags(
    mock_conn: Mock,
    mock_networks: Mock,
    openstack_item: OpenstackData,
    tags: list[str],
) -> None:
    """Check networks in the returned service."""
    openstack_item.provider_conf.network_tags = tags
    mock_networks.return_value = []
    endpoint = random_url()
    mock_conn.network.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_network_service()
    assert item is not None

    mock_networks.assert_called_once_with(
        default_private_net=None,
        default_public_net=None,
        proxy=None,
        tags=openstack_item.provider_conf.network_tags,
    )


@parametrize_with_cases("visibility", cases=CaseResourceVisibility, has_tag="default")
@patch("src.providers.openstack.OpenstackData.get_networks")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_service_default_net(
    mock_conn: Mock,
    mock_networks: Mock,
    openstack_item: OpenstackData,
    visibility: str,
) -> None:
    """Check networks in the returned service, passing default net attributes."""
    network_name = random_lower_string()
    if visibility == "public":
        openstack_item.project_conf.default_public_net = network_name
    else:
        openstack_item.project_conf.default_private_net = network_name
        openstack_item.project_conf.private_net_proxy = PrivateNetProxy(
            **private_net_proxy_dict()
        )
    mock_networks.return_value = []
    endpoint = random_url()
    mock_conn.network.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_network_service()
    assert item is not None

    mock_networks.assert_called_once_with(
        default_private_net=openstack_item.project_conf.default_private_net,
        default_public_net=openstack_item.project_conf.default_public_net,
        proxy=openstack_item.project_conf.private_net_proxy,
        tags=[],
    )
