from logging import getLogger
from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    NetworkCreateExtended,
    NetworkQuotaCreateExtended,
    NetworkServiceCreateExtended,
)
from fed_reg.service.enum import NetworkServiceName, ServiceType
from keystoneauth1.exceptions.catalog import EndpointNotFound
from pytest_cases import case, parametrize_with_cases

from src.models.provider import Openstack, PrivateNetProxy, Project
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    private_net_proxy_dict,
    project_dict,
    random_lower_string,
    random_url,
)


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
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_no_network_service(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    resp: EndpointNotFound | None,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    with patch("src.providers.openstack.Connection.network") as mock_srv:
        if resp:
            mock_srv.get_endpoint.side_effect = resp
        else:
            mock_srv.get_endpoint.return_value = resp
    mock_conn.network = mock_srv
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    assert not item.get_network_service()

    mock_srv.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_network_quotas")
@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_network_service_with_quotas(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_network: Mock,
    mock_network_quotas: Mock,
    user_quota: bool,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = {"network": {"per_user": True}} if user_quota else {}
    project_conf = Project(**project_dict(), per_user_limits=per_user_limits)
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
    mock_network_quotas.return_value = (
        NetworkQuotaCreateExtended(project=project_conf.id),
        NetworkQuotaCreateExtended(project=project_conf.id, usage=True),
    )
    mock_network.get_endpoint.return_value = endpoint
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_network_service()
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
@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_network_service_with_networks(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_network: Mock,
    mock_networks: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
    visibility: str,
) -> None:
    """Check networks in the returned service."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
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
                project=project_conf.id,
            )
        ]
    elif visibility == "no-access":
        mock_networks.return_value = []
    mock_network.get_endpoint.return_value = endpoint
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_network_service()
    if visibility == "no-access":
        assert len(item.networks) == 0
    else:
        assert len(item.networks) == 1


@parametrize_with_cases("tags", cases=CaseTagList)
@patch("src.providers.openstack.OpenstackData.get_networks")
@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_network_service_networks_tags(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_network: Mock,
    mock_networks: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
    tags: list[str],
) -> None:
    """Check networks in the returned service."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
        network_tags=tags,
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
    network = NetworkCreateExtended(uuid=uuid4(), name=random_lower_string())
    mock_networks.return_value = [network]
    mock_network.get_endpoint.return_value = endpoint
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_network_service()
    mock_networks.assert_called_once_with(
        default_private_net=None,
        default_public_net=None,
        proxy=None,
        tags=provider_conf.network_tags,
    )


@parametrize_with_cases("visibility", cases=CaseResourceVisibility, has_tag="default")
@patch("src.providers.openstack.OpenstackData.get_networks")
@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_network_service_default_net(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_network: Mock,
    mock_networks: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
    visibility: str,
) -> None:
    """Check networks in the returned service, passing default net attributes."""
    network_name = random_lower_string()
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    if visibility == "public":
        project_conf.default_public_net = network_name
    else:
        project_conf.default_private_net = network_name
        project_conf.private_net_proxy = PrivateNetProxy(**private_net_proxy_dict())
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
    mock_networks.return_value = []
    mock_network.get_endpoint.return_value = endpoint
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_network_service()
    mock_networks.assert_called_once_with(
        default_private_net=project_conf.default_private_net,
        default_public_net=project_conf.default_public_net,
        proxy=project_conf.private_net_proxy,
        tags=provider_conf.network_tags,
    )
