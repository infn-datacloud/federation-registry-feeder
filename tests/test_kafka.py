from logging import getLogger
from unittest.mock import Mock, patch

import pytest
from kafka.errors import NoBrokersAvailable
from pytest_cases import parametrize_with_cases

from src.kafka_conn import Producer, get_kafka_prod
from tests.schemas.utils import random_lower_string, random_url


class CaseHostname:
    def case_none(self) -> None:
        return None

    def case_str(self) -> str:
        """Should raise NoBrokersAvailable"""
        return random_lower_string()

    def case_url(self) -> str:
        """Should raise ValueError"""
        return random_url()


@patch("src.kafka_conn.KafkaProducer")
def test_kafka_producer(mock_producer: Mock) -> None:
    hostname = random_lower_string()
    topic = random_lower_string()
    prod = Producer(hostname=hostname, topic=topic)
    assert prod is not None
    assert isinstance(prod, Producer)
    assert prod.hostname == hostname
    assert prod.topic == topic
    assert prod.client_id == "Federation-Registry-Feeder"
    assert prod.producer is not None


def test_kafka_producer_no_borker() -> None:
    hostname = random_lower_string()
    topic = random_lower_string()
    with pytest.raises(NoBrokersAvailable):
        Producer(hostname=hostname, topic=topic)


def test_kafka_producer_invalid_hostname() -> None:
    hostname = random_url()
    topic = random_lower_string()
    with pytest.raises(ValueError):
        Producer(hostname=hostname, topic=topic)


@parametrize_with_cases("hostname", cases=CaseHostname)
def test_get_kafka_prod_none(hostname: str | None) -> None:
    prod = get_kafka_prod(
        hostname=hostname, topic=random_lower_string(), logger=getLogger("test")
    )
    assert prod is None


@patch("src.kafka_conn.KafkaProducer")
def test_get_kafka_prod(mock_producer: Mock) -> None:
    hostname = random_lower_string()
    topic = random_lower_string()
    prod = get_kafka_prod(
        hostname=hostname,
        topic=topic,
        logger=getLogger("test"),
    )
    assert prod is not None
    assert isinstance(prod, Producer)
    assert prod.hostname == hostname
    assert prod.topic == topic
    assert prod.client_id == "Federation-Registry-Feeder"
    assert prod.producer is not None


@patch("src.kafka_conn.KafkaProducer")
def test_send(mock_producer: Mock) -> None:
    data = {"key": "value"}
    hostname = random_lower_string()
    topic = random_lower_string()
    prod = Producer(hostname=hostname, topic=topic)
    value = prod.send(data)
    assert value is not None
