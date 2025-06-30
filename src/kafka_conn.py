import json
from logging import Logger
from typing import Any

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from src.models.config import Settings


class Producer:
    """Producer instance to send messages to kafka"""

    def __init__(self, *, settings: Settings, logger: Logger) -> None:
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
        """Organize quotas data and send them to kafka."""
        msg_version = msg_version
        for item in data:
            provider_conf = item.pop("provider_conf")
            issuer = item.pop("issuer")
            project = item.pop("project")
            identity_services = item.pop("identity_services")
            message = {
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
                **item,
            }
            message = json.loads(json.dumps(message, default=str))
            self.producer.send(topic, message)
            self.logger.info("Sending message")
            self.logger.debug("Data: %d", message)
        self.producer.flush()
        self.producer.close()


def get_kafka_prod(*, settings: Settings, logger=Logger) -> Producer:
    """Return kafka producer if broker exists."""
    try:
        return Producer(settings=settings, logger=logger)
    except NoBrokersAvailable:
        logger.error("No brokers available at %s", settings.KAFKA_BOOTSTRAP_SERVERS)
    except (ValueError, FileNotFoundError) as e:
        logger.error(e)
