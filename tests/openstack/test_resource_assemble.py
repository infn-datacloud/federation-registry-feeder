from random import randint
from uuid import uuid4

import pytest
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import Limits, PerRegionProps, PrivateNetProxy, Project
from src.providers.openstack import get_project_conf_params
from tests.schemas.utils import random_ip, random_lower_string


def get_block_storage_quota() -> BlockStorageQuotaBase:
    """Fixture with an SLA without projects."""
    return BlockStorageQuotaBase(
        gigabytes=randint(0, 100),
        per_volume_gigabytes=randint(0, 100),
        volumes=randint(1, 100),
    )


def get_compute_quota() -> ComputeQuotaBase:
    """Fixture with an SLA without projects."""
    return ComputeQuotaBase(
        cores=randint(0, 100),
        instances=randint(0, 100),
        ram=randint(1, 100),
    )


def get_network_quota() -> NetworkQuotaBase:
    """Fixture with an SLA without projects."""
    return NetworkQuotaBase(
        public_ips=randint(0, 100),
        networks=randint(0, 100),
        ports=randint(1, 100),
        security_groups=randint(1, 100),
        security_group_rules=randint(1, 100),
    )


def get_per_user_limits() -> Limits:
    block_storage_quota = get_block_storage_quota()
    compute_quota = get_compute_quota()
    network_quota = get_network_quota()
    return Limits(
        block_storage=block_storage_quota, compute=compute_quota, network=network_quota
    )


def get_private_net_proxy() -> PrivateNetProxy:
    return PrivateNetProxy(ip=random_ip(), user=random_lower_string())


@parametrize(per_region_props=[True, False])
def case_with_per_region_props(per_region_props: bool) -> bool:
    return per_region_props


@pytest.fixture
def region_props() -> PerRegionProps:
    return PerRegionProps(
        region_name=random_lower_string(),
        default_public_net=random_lower_string(),
        default_private_net=random_lower_string(),
        private_net_proxy=get_private_net_proxy(),
        per_user_limits=get_per_user_limits(),
    )


@pytest.fixture
def project() -> Project:
    return Project(
        id=uuid4(),
        sla=uuid4(),
        default_public_net=random_lower_string(),
        default_private_net=random_lower_string(),
        private_net_proxy=get_private_net_proxy(),
        per_user_limits=get_per_user_limits(),
    )


@parametrize_with_cases("with_per_region_props", cases=".")
def test_project_conf_based_on_region(
    project: Project, with_per_region_props: bool, region_props: PerRegionProps
) -> None:
    original_per_project_len = len(project.per_region_props)
    new_conf = get_project_conf_params(
        project_conf=project,
        region_props=region_props if with_per_region_props else None,
    )
    assert new_conf.id == project.id
    assert new_conf.description == project.description
    assert new_conf.sla == project.sla
    if with_per_region_props:
        assert new_conf.default_private_net == region_props.default_private_net
        assert new_conf.default_public_net == region_props.default_public_net
        assert new_conf.private_net_proxy == region_props.private_net_proxy
        if new_conf.per_user_limits:
            assert (
                new_conf.per_user_limits.block_storage
                == region_props.per_user_limits.block_storage
            )
            assert (
                new_conf.per_user_limits.compute == region_props.per_user_limits.compute
            )
            assert (
                new_conf.per_user_limits.network == region_props.per_user_limits.network
            )
    else:
        assert new_conf.default_private_net == project.default_private_net
        assert new_conf.default_public_net == project.default_public_net
        assert new_conf.private_net_proxy == project.private_net_proxy
        if new_conf.per_user_limits:
            assert (
                new_conf.per_user_limits.block_storage
                == project.per_user_limits.block_storage
            )
            assert new_conf.per_user_limits.compute == project.per_user_limits.compute
            assert new_conf.per_user_limits.network == project.per_user_limits.network
    assert len(new_conf.per_region_props) == 0
    assert len(project.per_region_props) == original_per_project_len
