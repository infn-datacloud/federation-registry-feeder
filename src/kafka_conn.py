"""Module to define kafka connection parameters and message details."""

import json
from datetime import datetime, timezone
from logging import Logger
from typing import Any

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from src.config import Settings
from src.providers.k8s import KubernetesClient
from src.providers.openstack import OpenstackClient


class Producer:
    """Producer instance to send messages to kafka."""

    def __init__(self, *, settings: Settings, logger: Logger) -> None:
        """Initializes a Kafka producer with the provided settings and logger.

        - Sets up Kafka producer with parameters such as client ID, bootstrap
            servers, value serializer, request size, acknowledgments, idempotence,
            and topic creation policy.
        - If SSL is enabled, reads the SSL password from the specified file and
            configures the producer with SSL certificates and keys.
        - Otherwise, initializes the producer without SSL.

        Args:
            settings (Settings): Configuration object containing Kafka connection
                parameters.
            logger (Logger): Logger instance for logging events and errors.

        """
        self.logger = logger
        self.topic = settings.KAFKA_TOPIC
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS

        kwargs = {
            "client_id": settings.KAFKA_CLIENT_NAME,
            "bootstrap_servers": self.bootstrap_servers,
            "value_serializer": lambda x: json.dumps(x, sort_keys=True).encode("utf-8"),
            "max_request_size": settings.KAFKA_MAX_REQUEST_SIZE,
            "acks": "all",
            "enable_idempotence": True,
            "allow_auto_create_topics": settings.KAFKA_ALLOW_AUTO_CREATE_TOPICS,
        }

        if settings.KAFKA_SSL_ENABLE:
            self.producer = KafkaProducer(
                security_protocol="SSL",
                ssl_check_hostname=False,
                ssl_cafile=settings.KAFKA_SSL_CACERT_PATH,
                ssl_certfile=settings.KAFKA_SSL_CERT_PATH,
                ssl_keyfile=settings.KAFKA_SSL_KEY_PATH,
                ssl_password=settings.KAFKA_SSL_PASSWORD,
                **kwargs,
            )
        else:
            self.producer = KafkaProducer(**kwargs)

    def send(self, clients: list[OpenstackClient]) -> None:
        """Sends a list of data items to a specified Kafka topic.

        - For each item in `data`, builds a message using `build_message`,
            serializes it to JSON, and sends it to the Kafka topic.
        - Logs information and debug details for each message sent.
        - Flushes and closes the Kafka producer after sending all messages.

        Args:
            clients (list of Client): A list of clients from which extrapolate data to
                be sent as messages.

        Returns:
            bool: True messages are successfully sent to kafka. False otherwise.

        """
        try:
            for item in clients:
                message = self.build_message(data=item)
                message = json.loads(json.dumps(message, default=str))
                self.producer.send(self.topic, message)
                self.logger.debug("Data: %s", message)
            self.producer.flush()
            self.logger.info("Sending messages")
            self.producer.close()
            return True
        except NoBrokersAvailable:
            msg = f"No brokers available at {self.bootstrap_servers}"
            self.logger.error(msg)
            return False

    def build_message(self, data: OpenstackClient | KubernetesClient) -> dict[str, Any]:
        """Builds a message dictionary for a specific message version.

        Parameters:
            data (dict[str, Any]): A dictionary containing the following required keys:
                - "provider_conf": dict with provider configuration, including "name",
                    "type", "regions", and "identity_providers".
                - "issuer": dict with issuer information, including "endpoint" and
                    "user_groups".
                - "project": dict with project information, including "uuid".
                - "identity_services": list of dicts, each with an "endpoint" key.
                Additional keys in `data` will be included in the resulting message.
            msg_version (str): The version of the message to build.

        Returns:
            dict: A dictionary representing the message, containing fields extracted and
                composed from the input data.

        Raises:
            KeyError: If any required key is missing from the input data.

        """
        msg = {
            "msg_version": "2.0.0",
            "provider_name": data.provider_name,
            "provider_type": data.provider_type,
            "identity_endpoint": data.provider_endpoint,
            "issuer_endpoint": data.idp_endpoint,
            "issuer_name": data.idp_name,
            "user_group": data.user_group,
            "project_id": data.project_id,
            "quotas": [i.model_dump() for i in data.quotas],
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

        if isinstance(data, OpenstackClient):
            msg["issuer_protocol"] = data.idp_protocol
            msg["region_name"] = data.region_name
            msg["overbooking_cpu"] = data.overbooking_cpu
            msg["overbooking_ram"] = data.overbooking_ram
            msg["bandwidth_in"] = data.bandwidth_in
            msg["bandwidth_out"] = data.bandwidth_out
            msg["flavors"] = [i.model_dump() for i in data.flavors]
            msg["images"] = [i.model_dump() for i in data.images]
            msg["networks"] = [i.model_dump() for i in data.networks]
        elif isinstance(data, OpenstackClient):
            msg["issuer_audience"] = data.idp_audience
            msg["storage_classes"] = [i.model_dump() for i in data.storage_classes]

        return msg
