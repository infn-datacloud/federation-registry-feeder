from typing import Any, Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    ObjectStoreQuotaCreateExtended,
    ObjectStoreServiceCreateExtended,
)
from fed_reg.service.enum import ObjectStoreServiceName, ServiceType
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits
from src.providers.openstack import OpenstackData
from tests.schemas.utils import random_lower_string, random_url


class CaseEndpointResp:
    def case_empty_catalog(self) -> list:
        return []

    def case_no_s3_type(self) -> list[dict[str, Any]]:
        return [
            {
                "endpoints": [],
                "id": uuid4().hex,
                "type": random_lower_string(),
                "name": "swift_s3",
            }
        ]

    def case_no_s3_swift_name(self) -> list[dict[str, Any]]:
        return [
            {
                "endpoints": [],
                "id": uuid4().hex,
                "type": "s3",
                "name": random_lower_string(),
            }
        ]

    def case_endpoint_dont_match_region(self) -> list[dict[str, Any]]:
        region = random_lower_string()
        return [
            {
                "endpoints": [
                    {
                        "id": uuid4().hex,
                        "interface": "public",
                        "region": region,
                        "region_id": region,
                        "url": random_url(),
                    }
                ],
                "id": uuid4().hex,
                "type": "s3",
                "name": "swift_s3",
            }
        ]

    def case_endpoint_not_public(self) -> list[dict[str, Any]]:
        region = random_lower_string()
        return [
            {
                "endpoints": [
                    {
                        "id": uuid4().hex,
                        "interface": random_lower_string(),
                        "region": region,
                        "region_id": region,
                        "url": random_url(),
                    }
                ],
                "id": uuid4().hex,
                "type": "s3",
                "name": "swift_s3",
            }
        ]


class CaseUserQuotaPresence:
    def case_present(self) -> Literal[True]:
        return True

    def case_absent(self) -> Literal[False]:
        return False


@parametrize_with_cases("resp", cases=CaseEndpointResp)
@patch("src.providers.openstack.Connection")
def test_no_s3_service(
    mock_conn: Mock, resp: list[dict[str, Any]], openstack_item: OpenstackData
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    # Set region name to match the once in the catalog only in a specific case
    if (
        len(resp) > 0
        and resp[0].get("type") == "s3"
        and resp[0].get("name") == "swift_s3"
        and resp[0].get("endpoints")[0].get("interface") != "public"
    ):
        openstack_item.region_name = resp[0].get("endpoints")[0].get("region")
    else:
        openstack_item.region_name = random_lower_string()

    mock_conn.service_catalog.__iter__.return_value = iter(resp)
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    openstack_item.conn = mock_conn

    s3_services = openstack_item.get_s3_services()
    assert not len(s3_services)
    mock_conn.service_catalog.__iter__.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_s3_quotas")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_s3_service_with_quotas(
    mock_conn: Mock,
    mock_s3_quotas: Mock,
    user_quota: bool,
    openstack_item: OpenstackData,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = Limits(
        **{"object_store": {"per_user": True}} if user_quota else {}
    )
    openstack_item.project_conf.per_user_limits = per_user_limits
    endpoint = random_url()
    mock_s3_quotas.return_value = (
        ObjectStoreQuotaCreateExtended(project=openstack_item.project_conf.id),
        ObjectStoreQuotaCreateExtended(
            project=openstack_item.project_conf.id, usage=True
        ),
    )

    mock_conn.service_catalog.__iter__.return_value = iter(
        [
            {
                "endpoints": [
                    {
                        "id": uuid4().hex,
                        "interface": "public",
                        "region": openstack_item.region_name,
                        "region_id": openstack_item.region_name,
                        "url": endpoint,
                    }
                ],
                "id": uuid4().hex,
                "type": "s3",
                "name": "swift_s3",
            }
        ]
    )
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    openstack_item.conn = mock_conn

    items = openstack_item.get_s3_services()
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ObjectStoreServiceCreateExtended)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.OBJECT_STORE.value
    assert item.name == ObjectStoreServiceName.OPENSTACK_SWIFT_S3.value
    if user_quota:
        assert len(item.quotas) == 3
        assert item.quotas[2].per_user
    else:
        assert len(item.quotas) == 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
