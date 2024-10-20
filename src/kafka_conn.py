import json
from logging import Logger
from typing import Any

from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ProviderCreateExtended,
)
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


def find_issuer_and_user_group(
    *, identity_providers: list[IdentityProviderCreateExtended], project: str
) -> tuple[str, str]:
    """Return issuer and user group matching project."""
    for issuer in identity_providers:
        for user_group in issuer.user_groups:
            if project == user_group.sla.project:
                return str(issuer.endpoint), user_group.name


def send_kafka_messages(*, kafka_prod: Producer, provider: ProviderCreateExtended):
    """Organize quotas data and send them to kafka."""
    for region in provider.regions:
        data_list = {}
        for service in [
            *region.block_storage_services,
            *region.compute_services,
            *region.network_services,
            *region.object_store_services,
        ]:
            service_type = service.type.replace("-", "_")
            service_endpoint = str(service.endpoint)
            for quota in service.quotas:
                data_list[quota.project] = data_list.get(quota.project, {})
                data_list[quota.project][service_endpoint] = data_list[
                    quota.project
                ].get(
                    service_endpoint,
                    {f"{service_type}_service": service_endpoint},
                )
                for k, v in quota.dict(
                    exclude={
                        "description",
                        "per_user",
                        "project",
                        "type",
                        "usage",
                    }
                ).items():
                    if quota.usage:
                        data_list[quota.project][service_endpoint][
                            f"{service_type}_usage_{k}"
                        ] = v
                    else:
                        data_list[quota.project][service_endpoint][
                            f"{service_type}_limit_{k}"
                        ] = v

        for project, value in data_list.items():
            issuer, user_group = find_issuer_and_user_group(
                identity_providers=provider.identity_providers, project=project
            )
            msg_data = {
                "provider": provider.name,
                "region": region.name,
                "project": project,
                "issuer": issuer,
                "user_group": user_group,
            }
            for data in value.values():
                msg_data = {**msg_data, **data}
            kafka_prod.send(msg_data)
