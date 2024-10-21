import logging
from typing import Any
from unittest.mock import Mock, patch

import pytest
from fed_reg.provider.schemas_extended import ProviderCreateExtended

from src.main import main
from src.models.config import APIVersions, Settings
from src.models.site_config import SiteConfig
from src.providers.openstack import OpenstackProviderException
from tests.fed_reg.utils import fed_reg_provider_dict, random_provider_status
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string, random_url


def site_config_dict() -> dict[str, Any]:
    sla = sla_dict()
    issuer = {
        **issuer_dict(),
        "token": random_lower_string(),
        "user_groups": [{**user_group_dict(), "slas": [sla]}],
    }
    auth_method = auth_method_dict()
    auth_method["endpoint"] = issuer["issuer"]
    project = project_dict()
    project["sla"] = sla["doc_uuid"]
    provider = {
        **openstack_dict(),
        "identity_providers": [auth_method],
        "projects": [project],
    }
    return {"trusted_idps": [issuer], "openstack": [provider]}


@patch("src.main.update_database", return_value=True)
def test_no_yaml_files(mock_edit_db: Mock) -> None:
    """No yaml files raise no error."""
    with patch("src.main.get_conf_files", return_value=[]):
        main(log_level=logging.INFO)

    mock_edit_db.assert_called_once()


@patch("src.main.update_database", return_value=True)
@patch("src.main.get_conf_files", return_value=[])
@patch("src.main.get_site_configs", return_value=([], True))
def test_invalid_site_configs(
    mock_get_configs: Mock, mock_load_files: Mock, mock_edit_db: Mock
) -> None:
    """Error when casting to object retrieved yaml files.

    We mock call to get_conf_files to avoid to load invalid files in the developer
    filesystem.
    """
    with pytest.raises(SystemExit):
        main(log_level=logging.INFO)

    mock_load_files.assert_called_once()
    mock_get_configs.assert_called_once()
    mock_edit_db.assert_called_once()


@patch("src.main.update_database", return_value=True)
@patch("src.main.get_conf_files", return_value=[])
@patch(
    "src.main.get_site_configs",
    return_value=([SiteConfig(**site_config_dict())], False),
)
@patch(
    "src.main.ProviderThread.get_provider",
    return_value=ProviderCreateExtended(
        **fed_reg_provider_dict(), status=random_provider_status(exclude="active")
    ),
)
def test_no_active_providers(
    mock_get_provider: Mock,
    mock_get_configs: Mock,
    mock_load_files: Mock,
    mock_edit_db: Mock,
) -> None:
    """No active providers should not raise error.

    We mock call to get_conf_files to avoid to load invalid files in the developer
    filesystem.
    """
    main(log_level=logging.INFO)

    mock_load_files.assert_called_once()
    mock_get_configs.assert_called_once()
    mock_get_provider.assert_called_once()
    mock_edit_db.assert_called_once()


@patch("src.main.update_database", return_value=True)
@patch("src.main.get_conf_files", return_value=[])
@patch(
    "src.main.get_site_configs",
    return_value=([SiteConfig(**site_config_dict())], False),
)
@patch("src.providers.conn_thread.ConnectionThread.__init__")
def test_error_in_provider_thread(
    mock_conn_thread: Mock,
    mock_get_configs: Mock,
    mock_load_files: Mock,
    mock_edit_db: Mock,
) -> None:
    """No active providers should not raise error.

    We mock call to get_conf_files to avoid to load invalid files in the developer
    filesystem.
    """
    mock_conn_thread.side_effect = OpenstackProviderException()
    with pytest.raises(SystemExit):
        main(log_level=logging.INFO)

    mock_load_files.assert_called_once()
    mock_get_configs.assert_called_once()
    mock_edit_db.assert_called_once()


@patch("src.main.update_database", return_value=False)
@patch("src.main.get_conf_files", return_value=[])
@patch(
    "src.main.get_site_configs",
    return_value=([SiteConfig(**site_config_dict())], False),
)
@patch(
    "src.main.ProviderThread.get_provider",
    return_value=ProviderCreateExtended(**fed_reg_provider_dict(), status="active"),
)
def test_db_update_error(
    mock_get_provider: Mock,
    mock_get_configs: Mock,
    mock_load_files: Mock,
    mock_edit_db: Mock,
) -> None:
    """Error received when communicating with Fed-Reg.

    We mock call to get_conf_files to avoid to load invalid files in the developer
    filesystem.
    """

    with pytest.raises(SystemExit):
        main(log_level=logging.INFO)

    mock_load_files.assert_called_once()
    mock_get_configs.assert_called_once()
    mock_get_provider.assert_called_once()
    mock_edit_db.assert_called_once()


@patch("src.main.update_database", return_value=True)
@patch("src.main.get_conf_files", return_value=[])
@patch(
    "src.main.get_site_configs",
    return_value=([SiteConfig(**site_config_dict())], False),
)
@patch(
    "src.main.ProviderThread.get_provider",
    return_value=ProviderCreateExtended(**fed_reg_provider_dict(), status="active"),
)
def test_main_success(
    mock_get_provider: Mock,
    mock_get_configs: Mock,
    mock_load_files: Mock,
    mock_edit_db: Mock,
) -> None:
    """Success.

    We mock call to get_conf_files to avoid to load invalid files in the developer
    filesystem.
    """

    main(log_level=logging.INFO)

    mock_load_files.assert_called_once()
    mock_get_configs.assert_called_once()
    mock_get_provider.assert_called_once()
    mock_edit_db.assert_called_once()


@patch("src.main.update_database", return_value=True)
@patch("src.main.get_conf_files", return_value=[])
@patch(
    "src.main.get_site_configs",
    return_value=([SiteConfig(**site_config_dict())], False),
)
@patch(
    "src.main.ProviderThread.get_provider",
    return_value=ProviderCreateExtended(**fed_reg_provider_dict(), status="active"),
)
@patch("src.main.send_kafka_messages")
def test_send_kafka_msg(
    mock_send_msg: Mock,
    mock_get_provider: Mock,
    mock_get_configs: Mock,
    mock_load_files: Mock,
    mock_edit_db: Mock,
) -> None:
    """Success and test kafka message sent.

    We mock call to get_conf_files to avoid to load invalid files in the developer
    filesystem.
    """

    with patch(
        "src.main.get_settings",
        return_value=Settings(
            KAFKA_HOSTNAME=random_url(),
            KAFKA_TOPIC=random_lower_string(),
            api_ver=APIVersions(),
        ),
    ):
        with patch("src.kafka_conn.KafkaProducer"):
            main(log_level=logging.INFO)

    mock_load_files.assert_called_once()
    mock_get_configs.assert_called_once()
    mock_get_provider.assert_called_once()
    mock_send_msg.assert_called_once()
    mock_edit_db.assert_called_once()
