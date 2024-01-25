import os
from random import getrandbits, randint
from typing import Dict, List, Optional
from unittest.mock import PropertyMock, patch
from uuid import uuid4

import pytest
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from app.service.enum import (
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
from tests.openstack.utils import random_image_visibility
from tests.schemas.utils import (
    random_float,
    random_image_os_type,
    random_ip,
    random_lower_string,
    random_url,
)


@case(tags=["endpoint_resp"])
@parametrize(raise_exc=[True, False])
def case_raise_exc(raise_exc: bool) -> bool:
    return raise_exc


@case(tags=["user_quotas"])
@parametrize(attr=[True, False])
def case_with_limits(attr: bool) -> bool:
    return attr


@case(tags=["tags"])
@parametrize(attr=range(3))
def case_tags(attr: int) -> Optional[List[str]]:
    if attr == 0:
        return None
    if attr == 1:
        return []
    if attr == 2:
        return ["none"]


@case(tags=["network"])
@parametrize(attr=["priv_net", "pub_net", "proxy"])
def case_attr(attr: str) -> str:
    return attr


@pytest.fixture
def block_storage_provider_quota() -> BlockStorageQuotaSet:
    return BlockStorageQuotaSet(
        backup_gigabytes=randint(0, 100),
        backups=randint(0, 100),
        gigabytes=randint(0, 100),
        groups=randint(0, 100),
        per_volume_gigabytes=randint(0, 100),
        snapshots=randint(0, 100),
        volumes=randint(0, 100),
    )


@pytest.fixture
def compute_provider_quota() -> ComputeQuotaSet:
    return ComputeQuotaSet(
        cores=randint(0, 100),
        fixed_ips=randint(0, 100),
        floating_ips=randint(0, 100),
        injected_file_content_bytes=randint(0, 100),
        injected_file_path_bytes=randint(0, 100),
        injected_files=randint(0, 100),
        instances=randint(0, 100),
        key_pairs=randint(0, 100),
        metadata_items=randint(0, 100),
        networks=randint(0, 100),
        ram=randint(0, 100),
        security_group_rules=randint(0, 100),
        security_groups=randint(0, 100),
        server_groups=randint(0, 100),
        server_group_members=randint(0, 100),
        force=False,
    )


@pytest.fixture
def network_provider_quota() -> NetworkQuota:
    return NetworkQuota(
        check_limit=False,
        floating_ips=randint(0, 100),
        health_monitors=randint(0, 100),
        listeners=randint(0, 100),
        load_balancers=randint(0, 100),
        l7_policies=randint(0, 100),
        networks=randint(0, 100),
        pools=randint(0, 100),
        ports=randint(0, 100),
        # project_id= ?,
        rbac_policies=randint(0, 100),
        routers=randint(0, 100),
        subnets=randint(0, 100),
        subnet_pools=randint(0, 100),
        security_group_rules=randint(0, 100),
        security_groups=randint(0, 100),
    )


@pytest.fixture
def block_storage_user_quota() -> BlockStorageQuotaBase:
    return BlockStorageQuotaBase(
        per_user=True,
        gigabytes=randint(0, 100),
        per_volume_gigabytes=randint(0, 100),
        volumes=randint(1, 100),
    )


@pytest.fixture
def compute_user_quota() -> ComputeQuotaBase:
    return ComputeQuotaBase(
        per_user=True,
        cores=randint(0, 100),
        instances=randint(0, 100),
        ram=randint(1, 100),
    )


@pytest.fixture
def network_user_quota() -> NetworkQuotaBase:
    return NetworkQuotaBase(
        per_user=True,
        public_ips=randint(0, 100),
        networks=randint(0, 100),
        ports=randint(1, 100),
        security_groups=randint(1, 100),
        security_group_rules=randint(1, 100),
    )


@pytest.fixture
def flavor() -> Flavor:
    return Flavor(
        name=random_lower_string(),
        description=random_lower_string(),
        disk=randint(0, 100),
        is_public=getrandbits(1),
        ram=randint(0, 100),
        vcpus=randint(0, 100),
        swap=randint(0, 100),
        ephemeral=randint(0, 100),
        is_disabled=False,
        rxtx_factor=random_float(0, 100),
        extra_specs={},
    )


@pytest.fixture
def image() -> Image:
    return Image(
        id=uuid4().hex,
        name=random_lower_string(),
        status="active",
        owner=uuid4().hex,
        os_type=random_image_os_type(),
        os_distro=random_lower_string(),
        os_version=random_lower_string(),
        architecture=random_lower_string(),
        kernel_id=random_lower_string(),
        visibility=random_image_visibility(),
        tags=["one"],
    )


@pytest.fixture
def network() -> Network:
    return Network(
        id=uuid4().hex,
        description=random_lower_string(),
        name=random_lower_string(),
        status="active",
        project_id=uuid4().hex,
        is_default=False,
        is_router_external=getrandbits(1),
        is_shared=getrandbits(1),
        mtu=randint(1, 100),
    )


@pytest.fixture
def proxy() -> PrivateNetProxy:
    return PrivateNetProxy(ip=random_ip(), user=random_lower_string())


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("raised_err", cases=".", has_tag="endpoint_resp")
def test_no_block_storage_service(mock_conn, raised_err: bool) -> None:
    with patch(
        "src.providers.openstack.Connection.block_storage"
    ) as mock_block_storage:
        if raised_err:
            mock_block_storage.get_endpoint.side_effect = EndpointNotFound()
        else:
            mock_block_storage.get_endpoint.return_value = None
    mock_conn.block_storage = mock_block_storage
    assert not get_block_storage_service(
        mock_conn, per_user_limits=None, project_id=uuid4().hex
    )


@patch("src.providers.openstack.Connection.block_storage")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("with_limits", cases=".", has_tag="user_quotas")
def test_retrieve_block_storage_service(
    mock_conn,
    mock_block_storage,
    block_storage_provider_quota: BlockStorageQuotaSet,
    block_storage_user_quota: BlockStorageQuotaBase,
    with_limits: bool,
) -> None:
    endpoint = random_url()
    mock_block_storage.get_endpoint.return_value = os.path.join(endpoint, uuid4().hex)
    mock_block_storage.get_quota_set.return_value = block_storage_provider_quota
    mock_conn.block_storage = mock_block_storage
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_block_storage_service(
        mock_conn,
        per_user_limits=block_storage_user_quota if with_limits else None,
        project_id=uuid4().hex,
    )
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.BLOCK_STORAGE.value
    assert item.name == BlockStorageServiceName.OPENSTACK_CINDER.value
    assert len(item.quotas) == 2 if with_limits else 1
    if with_limits:
        assert not item.quotas[0].per_user
        assert item.quotas[1].per_user


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("raised_err", cases=".", has_tag="endpoint_resp")
def test_no_compute_service(mock_conn, raised_err: bool) -> None:
    with patch("src.providers.openstack.Connection.compute") as mock_compute:
        if raised_err:
            mock_compute.get_endpoint.side_effect = EndpointNotFound()
        else:
            mock_compute.get_endpoint.return_value = None
        mock_conn.compute = mock_compute
        assert not get_compute_service(
            mock_conn, per_user_limits=None, project_id=uuid4().hex, tags=[]
        )


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("with_limits", cases=".", has_tag="user_quotas")
def test_retrieve_compute_service(
    mock_conn,
    mock_compute,
    compute_provider_quota: ComputeQuotaSet,
    compute_user_quota: ComputeQuotaBase,
    with_limits: bool,
) -> None:
    endpoint = random_url()
    mock_compute.get_endpoint.return_value = endpoint
    mock_compute.get_quota_set.return_value = compute_provider_quota
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_compute_service(
        mock_conn,
        per_user_limits=compute_user_quota if with_limits else None,
        project_id=uuid4().hex,
        tags=[],
    )
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.COMPUTE.value
    assert item.name == ComputeServiceName.OPENSTACK_NOVA.value
    assert len(item.quotas) == 2 if with_limits else 1
    if with_limits:
        assert not item.quotas[0].per_user
        assert item.quotas[1].per_user


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_service_with_flavors(
    mock_conn, mock_compute, flavor: Flavor
) -> None:
    def get_allowed_project_ids(*args, **kwargs) -> List[Dict[str, str]]:
        return [{"tenant_id": uuid4().hex}]

    endpoint = random_url()
    flavors = [flavor]
    mock_compute.get_endpoint.return_value = endpoint
    mock_compute.flavors.return_value = flavors
    mock_compute.get_flavor_access.side_effect = get_allowed_project_ids
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_compute_service(
        mock_conn,
        per_user_limits=None,
        project_id=uuid4().hex,
        tags=[],
    )
    assert len(item.flavors) == 1


@patch("src.providers.openstack.Connection.image")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=".", has_tag="tags")
def test_retrieve_compute_service_with_images(
    mock_conn, mock_compute, mock_image, image: Image, tags: Optional[List[str]]
) -> None:
    endpoint = random_url()
    images = list(
        filter(lambda x: set(x.tags).intersection(set(tags if tags else [])), [image])
    )
    mock_compute.get_endpoint.return_value = endpoint
    mock_conn.compute = mock_compute
    mock_image.images.return_value = images
    mock_conn.image = mock_image
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_compute_service(
        mock_conn,
        per_user_limits=None,
        project_id=uuid4().hex,
        tags=tags,
    )
    assert len(item.images) == len(images)


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("raised_err", cases=".", has_tag="endpoint_resp")
def test_no_network_service(mock_conn, raised_err: bool) -> None:
    with patch("src.providers.openstack.Connection.network") as mock_network:
        if raised_err:
            mock_network.get_endpoint.side_effect = EndpointNotFound()
        else:
            mock_network.get_endpoint.return_value = None
    mock_conn.network = mock_network
    assert not get_network_service(
        mock_conn,
        per_user_limits=None,
        project_id=uuid4().hex,
        tags=[],
        default_private_net=None,
        default_public_net=None,
        proxy=None,
    )


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("with_limits", cases=".", has_tag="user_quotas")
def test_retrieve_network_service(
    mock_conn,
    mock_network,
    network_provider_quota: NetworkQuota,
    network_user_quota: NetworkQuotaBase,
    with_limits: bool,
) -> None:
    endpoint = random_url()
    mock_network.get_endpoint.return_value = endpoint
    mock_network.get_quota_set.return_value = network_provider_quota
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_network_service(
        mock_conn,
        per_user_limits=network_user_quota if with_limits else None,
        project_id=uuid4().hex,
        tags=[],
        default_private_net=None,
        default_public_net=None,
        proxy=None,
    )
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.NETWORK.value
    assert item.name == NetworkServiceName.OPENSTACK_NEUTRON.value
    assert len(item.quotas) == 2 if with_limits else 1
    if with_limits:
        assert not item.quotas[0].per_user
        assert item.quotas[1].per_user


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("tags", cases=".", has_tag="tags")
def test_retrieve_network_service_with_networks(
    mock_conn, mock_network, network: Network, tags: Optional[List[str]]
) -> None:
    endpoint = random_url()
    networks = list(
        filter(lambda x: set(x.tags).intersection(set(tags if tags else [])), [network])
    )
    mock_network.get_endpoint.return_value = endpoint
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item = get_network_service(
        mock_conn,
        per_user_limits=None,
        project_id=uuid4().hex,
        tags=tags,
        default_private_net=None,
        default_public_net=None,
        proxy=None,
    )
    assert len(item.networks) == len(networks)


@patch("src.providers.openstack.Connection.network")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("attr", cases=".", has_tag="network")
def test_retrieve_network_service_additional_attrs(
    mock_conn, mock_network, network: Network, proxy: PrivateNetProxy, attr: str
) -> None:
    endpoint = random_url()
    if attr == "priv_net":
        network.is_default = False
        network.is_shared = False
    elif attr == "pub_net":
        network.is_default = False
        network.is_shared = True
    networks = [network]

    mock_network.get_endpoint.return_value = endpoint
    mock_network.networks.return_value = networks
    mock_conn.network = mock_network
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)

    item = get_network_service(
        mock_conn,
        per_user_limits=None,
        project_id=uuid4().hex,
        tags=[],
        default_private_net=network.name if attr == "priv_net" else None,
        default_public_net=network.name if attr == "pub_net" else None,
        proxy=proxy if attr == "proxy" else None,
    )

    assert len(item.networks) == len(networks)
    if attr == "priv_net":
        assert item.networks[0].is_default
    elif attr == "pub_net":
        assert item.networks[0].is_default
    elif attr == "proxy":
        assert item.networks[0].proxy_ip == str(proxy.ip)
        assert item.networks[0].proxy_user == proxy.user
