import os
from typing import List, Optional
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.quota.schemas import (
    BlockStorageQuotaBase,
    ComputeQuotaBase,
    NetworkQuotaBase,
)
from fed_reg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    NetworkServiceName,
    ServiceType,
)
from keystoneauth1.exceptions.catalog import EndpointNotFound
from openstack.block_storage.v3.quota_set import QuotaSet as BlockStorageQuotaSet
from openstack.compute.v2.flavor import Flavor
from openstack.compute.v2.quota_set import QuotaSet as ComputeQuotaSet
from openstack.image.v2.image import Image
from openstack.network.v2.network import Network
from openstack.network.v2.quota import Quota as NetworkQuota
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import PrivateNetProxy
from src.providers.openstack import (
    get_block_storage_service,
    get_compute_service,
    get_network_service,
)
from tests.providers.openstack.test_images import filter_images
from tests.providers.openstack.test_networks import filter_networks
from tests.schemas.utils import random_url


class CaseServiceType:
    @parametrize(type=["block_storage", "compute", "network"])
    def case_service(self, type: str) -> str:
        return type


class CaseEndpointResp:
    def case_raise_exc(self) -> EndpointNotFound:
        return EndpointNotFound()

    def case_none(self) -> None:
        return None


class CaseUserQuota:
    @case(tags=["block_storage"])
    @parametrize(presence=[True, False])
    def case_block_storage_quota(
        self, presence: bool, block_storage_quota: BlockStorageQuotaBase
    ) -> Optional[BlockStorageQuotaBase]:
        if presence:
            block_storage_quota.per_user = True
            return block_storage_quota
        return None

    @case(tags=["compute"])
    @parametrize(presence=[True, False])
    def case_compute_quota(
        self, presence: bool, compute_quota: ComputeQuotaBase
    ) -> Optional[ComputeQuotaBase]:
        if presence:
            compute_quota.per_user = True
            return compute_quota
        return None

    @case(tags=["network"])
    @parametrize(presence=[True, False])
    def case_network_quota(
        self, presence: bool, network_quota: NetworkQuotaBase
    ) -> Optional[NetworkQuotaBase]:
        if presence:
            network_quota.per_user = True
            return network_quota
        return None


class CaseTagList:
    @case(tags=["empty"])
    def case_empty_tag_list(self) -> Optional[List]:
        return []

    @case(tags=["empty"])
    def case_no_list(self) -> Optional[List]:
        return None

    @case(tags=["full"])
    def case_list(self) -> Optional[List]:
        return ["one"]


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("resp", cases=CaseEndpointResp)
@parametrize_with_cases("service", cases=CaseServiceType)
def test_no_block_storage_service(
    mock_conn: Mock, resp: Optional[EndpointNotFound], service: str
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    with patch(f"src.providers.openstack.Connection.{service}") as mock_srv:
        if resp:
            mock_srv.get_endpoint.side_effect = resp
        else:
            mock_srv.get_endpoint.return_value = resp
    mock_conn.__setattr__(service, mock_srv)
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    if service == "block_storage":
        assert not get_block_storage_service(mock_conn, per_user_limits=None)
    elif service == "compute":
        assert not get_compute_service(mock_conn, per_user_limits=None, tags=[])
    elif service == "network":
        assert not get_network_service(
            mock_conn,
            per_user_limits=None,
            tags=[],
            default_private_net=None,
            default_public_net=None,
            proxy=None,
        )


@patch("src.providers.openstack.Connection.block_storage")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuota, has_tag="block_storage")
def test_retrieve_block_storage_service(
    mock_conn: Mock,
    mock_block_storage: Mock,
    openstack_block_storage_quotas: BlockStorageQuotaSet,
    user_quota: Optional[BlockStorageQuotaBase],
) -> None:
    """Check quotas in the returned service."""
    endpoint = random_url()
    mock_block_storage.get_endpoint.return_value = os.path.join(endpoint, uuid4().hex)
    mock_block_storage.get_quota_set.return_value = openstack_block_storage_quotas
    mock_conn.block_storage = mock_block_storage
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_block_storage_service(mock_conn, per_user_limits=user_quota)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.BLOCK_STORAGE.value
    assert item.name == BlockStorageServiceName.OPENSTACK_CINDER.value
    assert len(item.quotas) == 3 if user_quota else 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
    if user_quota:
        assert item.quotas[2].per_user


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuota, has_tag="compute")
def test_retrieve_compute_service(
    mock_conn: Mock,
    mock_compute: Mock,
    openstack_compute_quotas: ComputeQuotaSet,
    user_quota: Optional[ComputeQuotaBase],
) -> None:
    """Check quotas in the returned service."""
    endpoint = random_url()
    mock_compute.get_endpoint.return_value = endpoint
    mock_compute.get_quota_set.return_value = openstack_compute_quotas
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_compute_service(mock_conn, per_user_limits=user_quota, tags=[])
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.COMPUTE.value
    assert item.name == ComputeServiceName.OPENSTACK_NOVA.value
    assert len(item.quotas) == 3 if user_quota else 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
    if user_quota:
        assert item.quotas[2].per_user


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuota, has_tag="network")
def test_retrieve_network_service(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_network_quotas: NetworkQuota,
    user_quota: Optional[NetworkQuotaBase],
) -> None:
    """Check quotas in the returned service."""
    endpoint = random_url()
    mock_network.get_endpoint.return_value = endpoint
    mock_network.get_quota_set.return_value = openstack_network_quotas
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_network_service(
        mock_conn,
        per_user_limits=user_quota,
        tags=[],
        default_private_net=None,
        default_public_net=None,
        proxy=None,
    )
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.NETWORK.value
    assert item.name == NetworkServiceName.OPENSTACK_NEUTRON.value
    assert len(item.quotas) == 3 if user_quota else 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
    if user_quota:
        assert item.quotas[2].per_user


@patch("src.providers.openstack.Connection.compute.get_flavor_access")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_service_with_flavors(
    mock_conn: Mock,
    mock_compute: Mock,
    mock_flavor_access: Mock,
    openstack_flavor_base: Flavor,
) -> None:
    """Check flavors in the returned service."""
    endpoint = random_url()
    project_id = uuid4().hex
    flavors = [openstack_flavor_base]
    mock_compute.get_endpoint.return_value = endpoint
    mock_compute.flavors.return_value = flavors
    mock_flavor_access.return_value = [{"tenant_id": project_id}]
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=project_id)
    item = get_compute_service(mock_conn, per_user_limits=None, tags=[])
    assert len(item.flavors) == 1


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=CaseTagList)
def test_retrieve_compute_service_with_images(
    mock_conn: Mock,
    mock_compute: Mock,
    mock_image: Mock,
    openstack_image_with_tags: Image,
    tags: Optional[List[str]],
) -> None:
    """Check images in the returned service.

    Check also that the tags filter is working properly.
    """
    endpoint = random_url()
    images = list(filter(lambda x: filter_images(x, tags), [openstack_image_with_tags]))
    mock_compute.get_endpoint.return_value = endpoint
    mock_conn.compute = mock_compute
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_image_with_tags.owner_id
    )
    item = get_compute_service(mock_conn, per_user_limits=None, tags=tags)
    assert len(item.images) == len(images)


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=CaseTagList)
def test_retrieve_network_service_with_networks(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_network_with_tags: Network,
    tags: Optional[List[str]],
) -> None:
    """Check networks in the returned service.

    Check also that the tags filter is working properly.
    """
    endpoint = random_url()
    networks = list(
        filter(lambda x: filter_networks(x, tags), [openstack_network_with_tags])
    )
    mock_network.get_endpoint.return_value = endpoint
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_network_with_tags.project_id
    )
    item = get_network_service(
        mock_conn,
        per_user_limits=None,
        tags=tags,
        default_private_net=None,
        default_public_net=None,
        proxy=None,
    )
    assert len(item.networks) == len(networks)


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_service_default_net(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_priv_pub_network: Network,
) -> None:
    """Check networks in the returned service, passing default net attributes."""
    endpoint = random_url()
    if openstack_priv_pub_network.is_shared:
        default_private_net = None
        default_public_net = openstack_priv_pub_network.name
    else:
        default_private_net = openstack_priv_pub_network.name
        default_public_net = None
    networks = [openstack_priv_pub_network]
    mock_network.get_endpoint.return_value = endpoint
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_priv_pub_network.project_id
    )
    item = get_network_service(
        mock_conn,
        per_user_limits=None,
        tags=[],
        default_private_net=default_private_net,
        default_public_net=default_public_net,
        proxy=None,
    )
    assert len(item.networks) == len(networks)
    assert item.networks[0].is_default


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
def test_retrieve_network_service_proxy(
    mock_conn: Mock,
    mock_network: Mock,
    openstack_network_base: Network,
    net_proxy: PrivateNetProxy,
) -> None:
    """Check networks in the returned service, passing proxy attributes."""
    endpoint = random_url()
    networks = [openstack_network_base]
    mock_network.get_endpoint.return_value = endpoint
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_network_base.project_id
    )
    item = get_network_service(
        mock_conn,
        per_user_limits=None,
        tags=[],
        default_private_net=None,
        default_public_net=None,
        proxy=net_proxy,
    )

    assert len(item.networks) == len(networks)
    assert item.networks[0].proxy_host == str(net_proxy.host)
    assert item.networks[0].proxy_user == net_proxy.user
