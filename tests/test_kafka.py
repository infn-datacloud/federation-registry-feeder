from logging import getLogger
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fed_reg.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    ComputeQuotaCreateExtended,
    IdentityProviderCreateExtended,
    NetworkQuotaCreateExtended,
    ObjectStoreQuotaCreateExtended,
    ProviderCreateExtended,
    RegionCreateExtended,
)
from kafka.errors import NoBrokersAvailable
from pytest_cases import parametrize, parametrize_with_cases

from src.kafka_conn import (
    Producer,
    find_issuer_and_user_group,
    get_kafka_prod,
    get_service_quotas,
    group_project_quotas,
    send_kafka_messages,
)
from tests.schemas.utils import random_lower_string, random_url


class CaseHostname:
    def case_none(self) -> None:
        return None

    def case_str(self) -> str:
        """Should raise NoBrokersAvailable"""
        return random_lower_string()

    def case_url(self) -> str:
        """Should raise ValueError"""
        return random_url()


class CaseQuota:
    @parametrize(usage=(True, False))
    def case_block_storage(self, usage: bool) -> BlockStorageQuotaCreateExtended:
        return BlockStorageQuotaCreateExtended(usage=usage, project=uuid4())

    @parametrize(usage=(True, False))
    def case_compute(self, usage: bool) -> ComputeQuotaCreateExtended:
        return ComputeQuotaCreateExtended(usage=usage, project=uuid4())

    @parametrize(usage=(True, False))
    def case_network(self, usage: bool) -> NetworkQuotaCreateExtended:
        return NetworkQuotaCreateExtended(usage=usage, project=uuid4())

    @parametrize(usage=(True, False))
    def case_object_store(self, usage: bool) -> ObjectStoreQuotaCreateExtended:
        return ObjectStoreQuotaCreateExtended(usage=usage, project=uuid4())


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


def test_find_issuer_and_user_group(
    identity_provider_create: IdentityProviderCreateExtended,
):
    project = identity_provider_create.user_groups[0].sla.project
    issuer, user_group = find_issuer_and_user_group(
        identity_providers=[identity_provider_create], project=project
    )
    assert issuer == str(identity_provider_create.endpoint)
    assert user_group == identity_provider_create.user_groups[0].name


def test_fail_to_find_issuer_and_user_group(
    identity_provider_create: IdentityProviderCreateExtended,
):
    project = uuid4()
    with pytest.raises(
        ValueError, match=f"No user group has an SLA matching project {project}"
    ):
        find_issuer_and_user_group(
            identity_providers=[identity_provider_create], project=project
        )


@parametrize_with_cases("quota", cases=CaseQuota)
def test_get_service_quota(
    quota: BlockStorageQuotaCreateExtended
    | ComputeQuotaCreateExtended
    | NetworkQuotaCreateExtended
    | ObjectStoreQuotaCreateExtended,
):
    exclude_attr = {"description", "per_user", "project", "type", "usage"}
    usage_limit = "usage" if quota.usage else "limit"
    qtype = quota.type.replace("-", "_")
    item = get_service_quotas(quota)
    for k in exclude_attr:
        assert f"{qtype}_{usage_limit}_{k}" not in item.keys()
    for k, v in quota.dict(exclude=exclude_attr).items():
        assert item[f"{qtype}_{usage_limit}_{k}"] == v


def test_group_project_quotas_no_project(region_create: RegionCreateExtended):
    project_quotas = group_project_quotas(region_create)
    assert project_quotas == {}


def test_group_project_quotas_single_project(region_create: RegionCreateExtended):
    project = uuid4()
    region_create.block_storage_services[0].quotas = [
        BlockStorageQuotaCreateExtended(usage=False, project=project),
        BlockStorageQuotaCreateExtended(usage=True, project=project),
    ]
    region_create.compute_services[0].quotas = [
        ComputeQuotaCreateExtended(usage=False, project=project),
        ComputeQuotaCreateExtended(usage=True, project=project),
    ]
    region_create.network_services[0].quotas = [
        NetworkQuotaCreateExtended(usage=False, project=project),
        NetworkQuotaCreateExtended(usage=True, project=project),
    ]
    region_create.object_store_services[0].quotas = [
        ObjectStoreQuotaCreateExtended(usage=False, project=project),
        ObjectStoreQuotaCreateExtended(usage=True, project=project),
    ]
    project_quotas = group_project_quotas(region_create)
    assert len(project_quotas.keys()) == 1
    data = project_quotas[project.hex]
    assert data is not None
    assert data["block_storage_service"] == str(
        region_create.block_storage_services[0].endpoint
    )
    assert data["compute_service"] == str(region_create.compute_services[0].endpoint)
    assert data["network_service"] == str(region_create.network_services[0].endpoint)
    assert data["object_store_service"] == str(
        region_create.object_store_services[0].endpoint
    )
    assert len(list(filter(lambda x: "block_storage_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "compute_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "network_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "object_store_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "block_storage_limit_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "compute_limit_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "network_limit_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "object_store_limit_" in x, data.keys()))) > 0


def test_group_project_quotas_multi_project(region_create: RegionCreateExtended):
    project1 = uuid4()
    project2 = uuid4()
    region_create.block_storage_services[0].quotas = [
        BlockStorageQuotaCreateExtended(usage=False, project=project1),
        BlockStorageQuotaCreateExtended(usage=True, project=project1),
    ]
    region_create.compute_services[0].quotas = [
        ComputeQuotaCreateExtended(usage=False, project=project1),
        ComputeQuotaCreateExtended(usage=True, project=project1),
    ]
    region_create.network_services[0].quotas = [
        NetworkQuotaCreateExtended(usage=False, project=project2),
        NetworkQuotaCreateExtended(usage=True, project=project2),
    ]
    region_create.object_store_services[0].quotas = [
        ObjectStoreQuotaCreateExtended(usage=False, project=project2),
        ObjectStoreQuotaCreateExtended(usage=True, project=project2),
    ]
    project_quotas = group_project_quotas(region_create)
    assert len(project_quotas.keys()) == 2
    data = project_quotas[project1.hex]
    assert data is not None
    assert data["block_storage_service"] == str(
        region_create.block_storage_services[0].endpoint
    )
    assert data["compute_service"] == str(region_create.compute_services[0].endpoint)
    assert data.get("network_service") is None
    assert data.get("object_store_service") is None
    assert len(list(filter(lambda x: "block_storage_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "compute_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "network_usage_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "object_store_usage_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "block_storage_limit_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "compute_limit_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "network_limit_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "object_store_limit_" in x, data.keys()))) == 0
    data = project_quotas[project2.hex]
    assert data is not None
    assert data.get("block_storage_service") is None
    assert data.get("compute_service") is None
    assert data["network_service"] == str(region_create.network_services[0].endpoint)
    assert data["object_store_service"] == str(
        region_create.object_store_services[0].endpoint
    )
    assert len(list(filter(lambda x: "block_storage_usage_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "compute_usage_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "network_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "object_store_usage_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "block_storage_limit_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "compute_limit_" in x, data.keys()))) == 0
    assert len(list(filter(lambda x: "network_limit_" in x, data.keys()))) > 0
    assert len(list(filter(lambda x: "object_store_limit_" in x, data.keys()))) > 0


@patch("src.kafka_conn.Producer")
def test_no_message_sent(mock_prod: Mock, provider_create: ProviderCreateExtended):
    send_kafka_messages(kafka_prod=mock_prod, providers=[provider_create])
    mock_prod.send.assert_not_called()


@patch("src.kafka_conn.Producer")
def test_send_messages(mock_prod: Mock, provider_create: ProviderCreateExtended):
    provider_create.regions[0].block_storage_services[0].quotas = [
        BlockStorageQuotaCreateExtended(
            usage=False, project=provider_create.projects[0].uuid
        ),
        BlockStorageQuotaCreateExtended(
            usage=True, project=provider_create.projects[0].uuid
        ),
    ]
    provider_create.regions[0].compute_services[0].quotas = [
        ComputeQuotaCreateExtended(
            usage=False, project=provider_create.projects[0].uuid
        ),
        ComputeQuotaCreateExtended(
            usage=True, project=provider_create.projects[0].uuid
        ),
    ]
    provider_create.regions[0].network_services[0].quotas = [
        NetworkQuotaCreateExtended(
            usage=False, project=provider_create.projects[0].uuid
        ),
        NetworkQuotaCreateExtended(
            usage=True, project=provider_create.projects[0].uuid
        ),
    ]
    provider_create.regions[0].object_store_services[0].quotas = [
        ObjectStoreQuotaCreateExtended(
            usage=False, project=provider_create.projects[0].uuid
        ),
        ObjectStoreQuotaCreateExtended(
            usage=True, project=provider_create.projects[0].uuid
        ),
    ]

    send_kafka_messages(kafka_prod=mock_prod, providers=[provider_create])

    block_storage_service = provider_create.regions[0].block_storage_services[0]
    compute_service = provider_create.regions[0].compute_services[0]
    network_service = provider_create.regions[0].network_services[0]
    object_store_service = provider_create.regions[0].object_store_services[0]

    exclude_attr = {"description", "per_user", "project", "type", "usage"}
    quotas = [
        *block_storage_service.quotas,
        *compute_service.quotas,
        *network_service.quotas,
        *object_store_service.quotas,
    ]
    data = {}
    for quota in quotas:
        qtype = quota.type.replace("-", "_")
        for k, v in quota.dict(exclude=exclude_attr).items():
            if quota.usage:
                data[f"{qtype}_usage_{k}"] = v
            else:
                data[f"{qtype}_limit_{k}"] = v

    mock_prod.send.assert_called_with(
        {
            "provider": provider_create.name,
            "region": provider_create.regions[0].name,
            "project": provider_create.projects[0].uuid,
            "issuer": str(provider_create.identity_providers[0].endpoint),
            "user_group": provider_create.identity_providers[0].user_groups[0].name,
            "block_storage_service": str(block_storage_service.endpoint),
            "compute_service": str(compute_service.endpoint),
            "network_service": str(network_service.endpoint),
            "object_store_service": str(object_store_service.endpoint),
            **data,
        }
    )
