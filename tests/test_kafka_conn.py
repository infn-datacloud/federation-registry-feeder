from unittest.mock import MagicMock, mock_open, patch

import pytest
from kafka.errors import NoBrokersAvailable

from src.kafka_conn import Producer, get_kafka_prod


@pytest.fixture
def mock_settings():
    class MockSettings:
        KAFKA_CLIENT_NAME = "test-client"
        KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
        KAFKA_MAX_REQUEST_SIZE = 1048576
        KAFKA_ALLOW_AUTO_CREATE_TOPICS = True
        KAFKA_ENABLE_SSL = False
        KAFKA_SSL_PASSWORD_PATH = None
        KAFKA_SSL_CACERT_PATH = None
        KAFKA_SSL_CERT_PATH = None
        KAFLA_SSL_KEY_PATH = None

    return MockSettings()


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("src.kafka_conn.KafkaProducer")
def test_producer_init_no_ssl(mock_kafka_producer, mock_settings, mock_logger):
    prod = Producer(settings=mock_settings, logger=mock_logger)
    mock_kafka_producer.assert_called_once()
    assert hasattr(prod, "producer")


@patch("src.kafka_conn.KafkaProducer")
def test_producer_init_with_ssl(mock_kafka_producer, mock_settings, mock_logger):
    mock_settings.KAFKA_ENABLE_SSL = True
    mock_settings.KAFKA_SSL_PASSWORD_PATH = "/tmp/ssl_password.txt"
    mock_settings.KAFKA_SSL_CACERT_PATH = "/tmp/ca.pem"
    mock_settings.KAFKA_SSL_CERT_PATH = "/tmp/cert.pem"
    mock_settings.KAFLA_SSL_KEY_PATH = "/tmp/key.pem"
    with patch("builtins.open", mock_open(read_data="password")):
        prod = Producer(settings=mock_settings, logger=mock_logger)
        mock_kafka_producer.assert_called_once()
        assert hasattr(prod, "producer")


@patch("src.kafka_conn.KafkaProducer")
def test_producer_init_ssl_missing_password_path(
    mock_kafka_producer, mock_settings, mock_logger
):
    mock_settings.KAFKA_ENABLE_SSL = True
    mock_settings.KAFKA_SSL_PASSWORD_PATH = None
    with pytest.raises(ValueError):
        Producer(settings=mock_settings, logger=mock_logger)


@patch("src.kafka_conn.KafkaProducer")
def test_send_message_and_build_message(
    mock_kafka_producer, mock_settings, mock_logger
):
    prod = Producer(settings=mock_settings, logger=mock_logger)
    prod.producer = MagicMock()
    data = [
        {
            "provider_conf": {
                "name": "prov1",
                "type": "type1",
                "regions": [
                    {
                        "name": "region1",
                        "overbooking_cpu": 2,
                        "overbooking_ram": 2,
                        "bandwidth_in": 100,
                        "bandwidth_out": 100,
                    }
                ],
                "identity_providers": [{"idp_name": "idp1", "protocol": "oidc"}],
            },
            "issuer": {
                "endpoint": "https://issuer",
                "user_groups": [{"name": "group1"}],
            },
            "project": {"uuid": "uuid1"},
            "identity_services": [{"endpoint": "https://id"}],
            "other": "value",
        }
    ]
    # Test build_message for default version (should match 1.2.0 logic)
    msg = prod.build_message(data=data[0].copy(), msg_version="1.2.0")
    assert msg["msg_version"] == "1.2.0"
    assert msg["provider_name"] == "prov1"
    assert msg["region_name"] == "region1"
    assert msg["issuer_name"] == "idp1"
    assert msg["issuer_protocol"] == "oidc"
    assert msg["user_group"] == "group1"
    assert msg["project_id"] == "uuid1"
    assert msg["other"] == "value"
    # Test send (calls build_message internally)
    prod.send(topic="test-topic", data=data, msg_version="1.2.0")
    prod.producer.send.assert_called()
    prod.producer.flush.assert_called_once()
    prod.producer.close.assert_called_once()


@patch("src.kafka_conn.Producer")
def test_get_kafka_prod_success(mock_producer, mock_settings, mock_logger):
    instance = MagicMock()
    mock_producer.return_value = instance
    result = get_kafka_prod(settings=mock_settings, logger=mock_logger)
    assert result == instance


@patch("src.kafka_conn.Producer", side_effect=NoBrokersAvailable)
def test_get_kafka_prod_no_brokers(mock_producer, mock_settings, mock_logger):
    result = get_kafka_prod(settings=mock_settings, logger=mock_logger)
    assert result is None
    mock_logger.error.assert_called_with(
        "No brokers available at %s", mock_settings.KAFKA_BOOTSTRAP_SERVERS
    )


@patch("src.kafka_conn.Producer", side_effect=ValueError("bad config"))
def test_get_kafka_prod_value_error(mock_producer, mock_settings, mock_logger):
    result = get_kafka_prod(settings=mock_settings, logger=mock_logger)
    assert result is None
    mock_logger.error.assert_called_with("bad config")


@patch("src.kafka_conn.Producer", side_effect=FileNotFoundError("missing file"))
def test_get_kafka_prod_file_not_found_error(mock_producer, mock_settings, mock_logger):
    result = get_kafka_prod(settings=mock_settings, logger=mock_logger)
    assert result is None
    mock_logger.error.assert_called_with("missing file")
