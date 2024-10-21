import json
from logging import Logger
from typing import Any

from fed_reg.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    ComputeQuotaCreateExtended,
    IdentityProviderCreateExtended,
    NetworkQuotaCreateExtended,
    ObjectStoreQuotaCreateExtended,
    ProviderCreateExtended,
    RegionCreateExtended,
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
    raise ValueError(f"No user group has an SLA matching project {project}")


def get_service_quotas(
    quota: BlockStorageQuotaCreateExtended
    | ComputeQuotaCreateExtended
    | NetworkQuotaCreateExtended
    | ObjectStoreQuotaCreateExtended,
) -> dict[str, Any]:
    data = {}
    exclude_attr = {"description", "per_user", "project", "type", "usage"}
    qtype = quota.type.replace("-", "_")
    for k, v in quota.dict(exclude=exclude_attr).items():
        if quota.usage:
            data[f"{qtype}_usage_{k}"] = v
        else:
            data[f"{qtype}_limit_{k}"] = v
    return data


def group_project_quotas(region: RegionCreateExtended) -> dict[str, Any]:
    project_quotas = {}
    services = [
        *region.block_storage_services,
        *region.compute_services,
        *region.network_services,
        *region.object_store_services,
    ]
    for service in services:
        service_type = service.type.replace("-", "_")
        service_endpoint = str(service.endpoint)
        service_data = {f"{service_type}_service": service_endpoint}
        for quota in service.quotas:
            qdata = get_service_quotas(quota)
            project_quotas[quota.project] = project_quotas.get(quota.project, {})
            project_quotas[quota.project].update(service_data)
            project_quotas[quota.project].update(qdata)
    return project_quotas


def send_kafka_messages(
    *, kafka_prod: Producer, providers: list[ProviderCreateExtended]
):
    """Organize quotas data and send them to kafka."""
    for provider in providers:
        for region in provider.regions:
            project_quotas = group_project_quotas(region)
            for project, values in project_quotas.items():
                issuer, user_group = find_issuer_and_user_group(
                    identity_providers=provider.identity_providers, project=project
                )
                msg_data = {
                    "provider": provider.name,
                    "region": region.name,
                    "project": project,
                    "issuer": issuer,
                    "user_group": user_group,
                    **values,
                }
                kafka_prod.send(msg_data)
