from logging import getLogger
from unittest.mock import Mock, patch

from src.models.provider import Openstack
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
)


@patch("src.providers.openstack.OpenstackData.create_connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_creation(mock_retrieve_info: Mock, mock_create_connection: Mock) -> None:
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    token = random_lower_string()
    logger = getLogger("test")
    item = OpenstackData(provider_conf=provider_conf, token=token, logger=logger)
    assert item is not None
    assert item.provider_conf == provider_conf
    assert item.project_conf == provider_conf.projects[0]
    assert item.auth_method == provider_conf.identity_providers[0]
    assert item.region_name == provider_conf.regions[0].name
    assert item.logger == logger
    assert item.conn is not None

    mock_create_connection.assert_called_once_with(token=token)
    mock_retrieve_info.assert_called_once()


def test_connection() -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    token = random_lower_string()
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        item = OpenstackData(
            provider_conf=provider_conf,
            token=token,
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
    assert item.conn.auth.get("access_token") == token
    assert item.conn.auth.get("project_id") == provider_conf.projects[0].id
    assert item.conn._compute_region == provider_conf.regions[0].name
