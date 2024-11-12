from logging import getLogger
from typing import Literal
from unittest.mock import Mock, patch

import pytest
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Openstack, Project, Region
from src.providers.openstack import OpenstackData, OpenstackProviderError
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    region_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string


class CaseNum:
    def case_0(self) -> Literal[0]:
        return 0

    def case_2(self) -> Literal[2]:
        return 2


@patch("src.providers.openstack.OpenstackData.create_connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_creation(mock_retrieve_info: Mock, mock_create_connection: Mock) -> None:
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [{**sla_dict()}]}],
    )
    logger = getLogger("test")
    item = OpenstackData(provider_conf=provider_conf, issuer=issuer, logger=logger)
    assert item is not None
    assert item.provider_conf == provider_conf
    assert item.project_conf == provider_conf.projects[0]
    assert item.auth_method == provider_conf.identity_providers[0]
    assert item.region_name == provider_conf.regions[0].name
    assert item.logger == logger
    assert item.conn is not None

    mock_create_connection.assert_called_once_with(token=issuer.token)
    mock_retrieve_info.assert_called_once()


def test_connection() -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [{**sla_dict()}]}],
    )
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        item = OpenstackData(
            provider_conf=provider_conf,
            issuer=issuer,
            logger=logger,
        )

    assert item.conn.auth.get("auth_url") == provider_conf.auth_url
    assert (
        item.conn.auth.get("identity_provider")
        == provider_conf.identity_providers[0].idp_name
    )
    assert (
        item.conn.auth.get("protocol") == provider_conf.identity_providers[0].protocol
    )
    assert item.conn.auth.get("access_token") == issuer.token
    assert item.conn.auth.get("project_id") == provider_conf.projects[0].id
    assert item.conn._compute_region == provider_conf.regions[0].name


@parametrize_with_cases("num", cases=CaseNum)
def test_failed_creation_because_regions(num: int) -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    if num == 0:
        provider_conf.regions.clear()
    else:
        provider_conf.regions.append(Region(**region_dict()))
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [{**sla_dict()}]}],
    )
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        with pytest.raises(OpenstackProviderError):
            OpenstackData(
                provider_conf=provider_conf,
                issuer=issuer,
                logger=logger,
            )


@parametrize_with_cases("num", cases=CaseNum)
def test_failed_creation_because_projects(num: int) -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    if num == 0:
        provider_conf.projects.clear()
    else:
        provider_conf.projects.append(Project(**project_dict()))
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [{**sla_dict()}]}],
    )
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        with pytest.raises(OpenstackProviderError):
            OpenstackData(
                provider_conf=provider_conf,
                issuer=issuer,
                logger=logger,
            )


@parametrize_with_cases("num", cases=CaseNum)
def test_failed_creation_because_idps(num: int) -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    if num == 0:
        provider_conf.identity_providers.clear()
    else:
        provider_conf.identity_providers.append(AuthMethod(**auth_method_dict()))
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [{**sla_dict()}]}],
    )
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        with pytest.raises(OpenstackProviderError):
            OpenstackData(
                provider_conf=provider_conf,
                issuer=issuer,
                logger=logger,
            )
