from random import randint

import pytest
from fed_reg.quota.schemas import (
    BlockStorageQuotaBase,
    ComputeQuotaBase,
    NetworkQuotaBase,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import (
    Limits,
    PerRegionProps,
    PrivateNetProxy,
    Project,
)
from src.providers.core import get_project_conf_params
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
    return PrivateNetProxy(host=random_ip(), user=random_lower_string())


@parametrize(per_region_props=[True, False])
def case_with_per_region_props(per_region_props: bool) -> bool:
    return per_region_props


@pytest.fixture
def per_region_props_with_specifics(per_region_props: PerRegionProps) -> PerRegionProps:
    per_region_props.default_public_net = random_lower_string()
    per_region_props.default_private_net = random_lower_string()
    per_region_props.private_net_proxy = get_private_net_proxy()
    per_region_props.per_user_limits = get_per_user_limits()
    return per_region_props


@pytest.fixture
def project_with_specifics(project: Project) -> Project:
    project.default_public_net = random_lower_string()
    project.default_private_net = random_lower_string()
    project.private_net_proxy = get_private_net_proxy()
    project.per_user_limits = get_per_user_limits()
    return project


@parametrize_with_cases("with_per_region_props", cases=".")
def test_project_conf_based_on_region(
    project_with_specifics: Project,
    with_per_region_props: bool,
    per_region_props_with_specifics: PerRegionProps,
) -> None:
    original_per_project_len = len(project_with_specifics.per_region_props)
    new_conf = get_project_conf_params(
        project_conf=project_with_specifics,
        region_props=per_region_props_with_specifics if with_per_region_props else None,
    )
    assert new_conf.id == project_with_specifics.id
    assert new_conf.description == project_with_specifics.description
    assert new_conf.sla == project_with_specifics.sla
    if with_per_region_props:
        assert (
            new_conf.default_private_net
            == per_region_props_with_specifics.default_private_net
        )
        assert (
            new_conf.default_public_net
            == per_region_props_with_specifics.default_public_net
        )
        assert (
            new_conf.private_net_proxy
            == per_region_props_with_specifics.private_net_proxy
        )
        if new_conf.per_user_limits:
            assert (
                new_conf.per_user_limits.block_storage
                == per_region_props_with_specifics.per_user_limits.block_storage
            )
            assert (
                new_conf.per_user_limits.compute
                == per_region_props_with_specifics.per_user_limits.compute
            )
            assert (
                new_conf.per_user_limits.network
                == per_region_props_with_specifics.per_user_limits.network
            )
    else:
        assert (
            new_conf.default_private_net == project_with_specifics.default_private_net
        )
        assert new_conf.default_public_net == project_with_specifics.default_public_net
        assert new_conf.private_net_proxy == project_with_specifics.private_net_proxy
        if new_conf.per_user_limits:
            assert (
                new_conf.per_user_limits.block_storage
                == project_with_specifics.per_user_limits.block_storage
            )
            assert (
                new_conf.per_user_limits.compute
                == project_with_specifics.per_user_limits.compute
            )
            assert (
                new_conf.per_user_limits.network
                == project_with_specifics.per_user_limits.network
            )
    assert len(new_conf.per_region_props) == 0
    assert len(project_with_specifics.per_region_props) == original_per_project_len
