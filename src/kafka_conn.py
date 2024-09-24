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
        logger: Logger,
        client_id: str = "Federation-Registry-Feeder",
        **kwargs,
    ) -> None:
        self.server_url = server_url
        self.topic = topic
        self.logger = logger
        self.client_id = client_id
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.server_url,
                client_id=client_id,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                **kwargs,
            )
        except NoBrokersAvailable:
            self.logger.error("No brokers available at %s", self.server_url)
            self.producer = None

    def send(self, data: dict[str, Any]):
        """Send message to kafka"""
        self.producer.send(self.topic, data)
