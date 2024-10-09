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
