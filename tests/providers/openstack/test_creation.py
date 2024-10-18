from logging import getLogger
from unittest.mock import Mock, patch

from fed_reg.provider.schemas_extended import IdentityProviderCreateExtended

from src.models.provider import Openstack, Project
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
)


@patch("src.providers.openstack.OpenstackData.create_connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_creation(
    mock_retrieve_info: Mock,
    mock_create_connection: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
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
    assert item is not None
    assert item.provider_conf == provider_conf
    assert item.project_conf == project_conf
    assert item.identity_provider == identity_provider_create
    assert item.region_name == region_name
    assert item.logger == logger
    assert item.conn is not None

    mock_create_connection.assert_called_once_with(token=token)
    mock_retrieve_info.assert_called_once()


@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_connection(
    mock_retrieve_info: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
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

    assert item.conn.auth.get("auth_url") == provider_conf.auth_url
    assert (
        item.conn.auth.get("identity_provider")
        == identity_provider_create.relationship.idp_name
    )
    assert (
        item.conn.auth.get("protocol") == identity_provider_create.relationship.protocol
    )
    assert item.conn.auth.get("access_token") == token
    assert item.conn.auth.get("project_id") == project_conf.id
    assert item.conn._compute_region == region_name
