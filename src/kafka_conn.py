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
        server_url: str,
        topic: str,
        client_id: str = "Federation-Registry-Feeder",
        **kwargs,
    ) -> None:
        self.server_url = server_url
        self.topic = topic
        self.client_id = client_id
        self.producer = KafkaProducer(
            bootstrap_servers=self.server_url,
            client_id=client_id,
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            **kwargs,
        )

    def send(self, data: dict[str, Any]):
        """Send message to kafka"""
        self.producer.send(self.topic, data)


def get_kafka_prod(
    *, url: str | None, topic: str | None, logger: Logger
) -> Producer | None:
    """Return kafka producer if broker exists."""
    if not (url is None or topic is None):
        try:
            return Producer(server_url=url, topic=topic)
        except NoBrokersAvailable:
            logger.warning("No brokers available at %s", url)
    return None
