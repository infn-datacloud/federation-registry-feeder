import json
from logging import Logger
from typing import Any

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from src.models.config import Settings


class Producer:
    """Producer instance to send messages to kafka"""

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

        Raises:
            ValueError: If SSL is enabled but the SSL password path is not provided.

        """
        self.logger = logger
        kwargs = {
            "client_id": settings.KAFKA_CLIENT_NAME,
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "value_serializer": lambda x: json.dumps(x, sort_keys=True).encode("utf-8"),
            "max_request_size": settings.KAFKA_MAX_REQUEST_SIZE,
            "acks": "all",
            "enable_idempotence": True,
            "allow_auto_create_topics": settings.KAFKA_ALLOW_AUTO_CREATE_TOPICS,
        }

        if settings.KAFKA_ENABLE_SSL:
            if settings.KAFKA_SSL_PASSWORD_PATH is None:
                raise ValueError(
                    "KAFKA_SSL_PASSWORD_PATH can't be None when KAFKA_ENABLE_SSL is "
                    "True"
                )
            with open(settings.KAFKA_SSL_PASSWORD_PATH) as reader:
                ssl_password = reader.read()
            self.producer = KafkaProducer(
                security_protocol="SSL",
                ssl_check_hostname=False,
                ssl_passwordfile=settings.KAFKA_SSL_PASSWORD_PATH,
                ssl_cafile=settings.KAFKA_SSL_CACERT_PATH,
                ssl_certfile=settings.KAFKA_SSL_CERT_PATH,
                ssl_keyfile=settings.KAFLA_SSL_KEY_PATH,
                ssl_password=ssl_password,
                **kwargs,
            )
        else:
            self.producer = KafkaProducer(**kwargs)

    def send(self, *, topic: str, data: list[dict[str, Any]], msg_version: str):
        """Sends a list of data items to a specified Kafka topic.

        - For each item in `data`, builds a message using `build_message`,
            serializes it to JSON, and sends it to the Kafka topic.
        - Logs information and debug details for each message sent.
        - Flushes and closes the Kafka producer after sending all messages.

        Args:
            topic (str): The Kafka topic to which messages will be sent.
            data (list[dict[str, Any]]): A list of data dictionaries to be sent as
                messages.
            msg_version (str): The version identifier to include in each message.

        """
        msg_version = msg_version
        for item in data:
            message = self.build_message(data=item, msg_version=msg_version)
            message = json.loads(json.dumps(message, default=str))
            self.producer.send(topic, message)
            self.logger.info("Sending message")
            self.logger.debug("Data: %d", message)
        self.producer.flush()
        self.producer.close()

    def build_message(self, *, data: dict[str, Any], msg_version: str):
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
        provider_conf = data.pop("provider_conf")
        issuer = data.pop("issuer")
        project = data.pop("project")
        identity_services = data.pop("identity_services")
        if msg_version == "1.2.0":
            return {
                "msg_version": msg_version,
                "provider_name": provider_conf["name"],
                "provider_type": provider_conf["type"],
                "identity_endpoint": identity_services[0]["endpoint"],
                "region_name": provider_conf["regions"][0]["name"],
                "overbooking_cpu": provider_conf["regions"][0]["overbooking_cpu"],
                "overbooking_ram": provider_conf["regions"][0]["overbooking_ram"],
                "bandwidth_in": provider_conf["regions"][0]["bandwidth_in"],
                "bandwidth_out": provider_conf["regions"][0]["bandwidth_out"],
                "issuer_endpoint": issuer["endpoint"],
                "issuer_name": provider_conf["identity_providers"][0]["idp_name"],
                "issuer_protocol": provider_conf["identity_providers"][0]["protocol"],
                "user_group": issuer["user_groups"][0]["name"],
                "project_id": project["uuid"],
                **data,
            }


def get_kafka_prod(*, settings: Settings, logger: Logger) -> Producer:
    """Creates a Kafka producer instance using the provided settings and logger.

    Args:
        settings (Settings): Configuration object containing Kafka connection
            parameters.
        logger (Logger, optional): Logger instance for logging errors.

    Returns:
        Producer: An instance of the Kafka Producer if the broker is available.

    Raises:
        NoBrokersAvailable: If no Kafka brokers are available at the specified address.
        ValueError: If there is a value error during producer creation.
        FileNotFoundError: If a required file is not found during producer creation.

    """
    try:
        return Producer(settings=settings, logger=logger)
    except NoBrokersAvailable:
        logger.error("No brokers available at %s", settings.KAFKA_BOOTSTRAP_SERVERS)
    except (ValueError, FileNotFoundError) as e:
        logger.error(e.args[0])
