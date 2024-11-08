import json
from logging import getLogger
from unittest.mock import Mock, patch

import pytest
from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
)
from kafka.errors import NoBrokersAvailable
from pytest_cases import parametrize_with_cases

from src.kafka_conn import Producer, get_kafka_prod, send_kafka_messages
from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    kubernetes_dict,
    openstack_dict,
    project_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string, random_url


class CaseProviderIssuer:
    def case_openstack(self) -> tuple[Openstack, Issuer]:
        provider = Openstack(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return provider, issuer

    def case_k8s(self) -> tuple[Kubernetes, Issuer]:
        provider = Kubernetes(
            **kubernetes_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return provider, issuer


class CaseHostname:
    def case_none(self) -> None:
        return None

    def case_str(self) -> str:
        """Should raise NoBrokersAvailable"""
        return random_lower_string()

    def case_url(self) -> str:
        """Should raise ValueError"""
        return random_url()


def test_kafka_producer() -> None:
    hostname = random_lower_string()
    topic = random_lower_string()
    with patch("src.kafka_conn.KafkaProducer"):
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


def test_get_kafka_prod() -> None:
    hostname = random_lower_string()
    topic = random_lower_string()
    with patch("src.kafka_conn.KafkaProducer"):
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


def test_send() -> None:
    data = {"key": "value"}
    hostname = random_lower_string()
    topic = random_lower_string()
    with patch("src.kafka_conn.KafkaProducer"):
        prod = Producer(hostname=hostname, topic=topic)
        value = prod.send(data)
        assert value is not None


@patch("src.kafka_conn.Producer")
def test_no_message_sent(mock_prod: Mock):
    send_kafka_messages(kafka_prod=mock_prod, connections_data=[])
    mock_prod.send.assert_not_called()


@patch("src.kafka_conn.Producer")
@parametrize_with_cases("provider_conf, issuer", cases=CaseProviderIssuer)
def test_send_messages(
    mock_prod: Mock,
    provider_conf: Openstack | Kubernetes,
    issuer: Issuer,
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    identity_service_create: IdentityServiceCreate,
    network_service_create: NetworkServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
):
    connection_data = {
        "provider_conf": provider_conf.dict(),
        "issuer": issuer.dict(),
        "project": project_create.dict(),
        "block_storage_services": [block_storage_service_create.dict()],
        "compute_services": [compute_service_create.dict()],
        "identity_services": [identity_service_create.dict()],
        "network_services": [network_service_create.dict()],
        "object_store_services": [s3_service_create.dict()],
    }

    send_kafka_messages(kafka_prod=mock_prod, connections_data=[{**connection_data}])

    mock_prod.send.assert_called_with(
        json.dumps(
            {
                "msg_version": "1.0.0",
                "provider_name": connection_data["provider_conf"]["name"],
                "provider_type": connection_data["provider_conf"]["type"],
                "region_name": connection_data["provider_conf"]["regions"][0]["name"],
                "issuer_endpoint": connection_data["issuer"]["endpoint"],
                "user_group": connection_data["issuer"]["user_groups"][0]["name"],
                "project_id": connection_data["project"]["uuid"],
                "block_storage_services": connection_data["block_storage_services"],
                "compute_services": connection_data["compute_services"],
                "identity_services": connection_data["identity_services"],
                "network_services": connection_data["network_services"],
                "object_store_services": connection_data["object_store_services"],
            }
        )
    )
