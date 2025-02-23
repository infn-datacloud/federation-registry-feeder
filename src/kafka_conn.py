import json
from logging import Logger
from typing import Any

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


class Producer:
    """Producer instance to send messages to kafka"""

    def __init__(
        self,
        *,
        hostname: str,
        topic: str,
        client_id: str = "Federation-Registry-Feeder",
        **kwargs,
    ) -> None:
        self.hostname = hostname
        self.topic = topic
        self.client_id = client_id
        self.producer = KafkaProducer(
            bootstrap_servers=self.hostname,
            client_id=client_id,
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            **kwargs,
        )

    def send(self, data: dict[str, Any]) -> Any:
        """Send message to kafka"""
        return self.producer.send(self.topic, data)


def get_kafka_prod(
    *, hostname: str | None, topic: str | None, logger: Logger
) -> Producer | None:
    """Return kafka producer if broker exists."""
    if not (hostname is None or topic is None):
        try:
            return Producer(hostname=hostname, topic=topic)
        except NoBrokersAvailable:
            logger.error("No brokers available at %s", hostname)
        except ValueError as e:
            logger.error(e)
    return None


def send_kafka_messages(
    *, kafka_prod: Producer, connections_data: list[dict[str, Any]]
):
    """Organize quotas data and send them to kafka."""
    msg_version = "1.1.0"
    for data in connections_data:
        provider_conf = data.pop("provider_conf")
        issuer = data.pop("issuer")
        project = data.pop("project")
        message = {
            "msg_version": msg_version,
            "provider_name": provider_conf["name"],
            "provider_type": provider_conf["type"],
            "region_name": provider_conf["regions"][0]["name"],
            "overbooking_cpu": provider_conf["regions"][0]["overbooking_cpu"],
            "overbooking_ram": provider_conf["regions"][0]["overbooking_ram"],
            "bandwidth_in": provider_conf["regions"][0]["bandwidth_in"],
            "bandwidth_out": provider_conf["regions"][0]["bandwidth_out"],
            "issuer_endpoint": issuer["endpoint"],
            "user_group": issuer["user_groups"][0]["name"],
            "project_id": project["uuid"],
            **data,
        }
        message = json.loads(json.dumps(message, default=str))
        kafka_prod.send(message)
