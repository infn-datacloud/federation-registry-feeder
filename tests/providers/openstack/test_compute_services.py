from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    ImageCreateExtended,
)
from fed_reg.service.enum import ComputeServiceName, ServiceType
from keystoneauth1.exceptions.catalog import EndpointNotFound
from pytest_cases import parametrize_with_cases

from src.models.provider import Limits
from src.providers.openstack import OpenstackData
from tests.schemas.utils import random_lower_string, random_url


class CaseEndpointResp:
    def case_raise_exc(self) -> EndpointNotFound:
        return EndpointNotFound()

    def case_none(self) -> None:
        return None


class CaseUserQuotaPresence:
    def case_present(self) -> Literal[True]:
        return True

    def case_absent(self) -> Literal[False]:
        return False


class CaseResourceVisibility:
    def case_public(self) -> Literal["public"]:
        return "public"

    def case_private(self) -> Literal["private"]:
        return "private"

    def case_not_accessible(self) -> Literal["no-access"]:
        return "no-access"


class CaseTagList:
    def case_empty_list(self) -> list:
        return []

    def case_list(self) -> list[str]:
        return ["one"]


@parametrize_with_cases("resp", cases=CaseEndpointResp)
@patch("src.providers.openstack.Connection")
def test_no_compute_service(
    mock_conn: Mock, resp: EndpointNotFound | None, openstack_item: OpenstackData
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    if resp:
        mock_conn.compute.get_endpoint.side_effect = resp
    else:
        mock_conn.compute.get_endpoint.return_value = resp
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    assert not openstack_item.get_compute_service()
    if resp:
        assert openstack_item.error
    mock_conn.compute.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_compute_quotas")
@patch("src.providers.openstack.Connection")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_compute_service_with_quotas(
    mock_conn: Mock,
    mock_compute_quotas: Mock,
    user_quota: bool,
    openstack_item: OpenstackData,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = Limits(**{"compute": {"per_user": True}} if user_quota else {})
    openstack_item.project_conf.per_user_limits = per_user_limits
    mock_compute_quotas.return_value = (
        ComputeQuotaCreateExtended(project=openstack_item.project_conf.id),
        ComputeQuotaCreateExtended(project=openstack_item.project_conf.id, usage=True),
    )
    endpoint = random_url()
    mock_conn.compute.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_compute_service()
    assert isinstance(item, ComputeServiceCreateExtended)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.COMPUTE.value
    assert item.name == ComputeServiceName.OPENSTACK_NOVA.value
    if user_quota:
        assert len(item.quotas) == 3
        assert item.quotas[2].per_user
    else:
        assert len(item.quotas) == 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
    assert len(item.flavors) == 0
    assert len(item.images) == 0


@parametrize_with_cases("visibility", cases=CaseResourceVisibility)
@patch("src.providers.openstack.OpenstackData.get_flavors")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_service_with_flavors(
    mock_conn: Mock,
    mock_flavors: Mock,
    openstack_item: OpenstackData,
    visibility: str,
) -> None:
    """Check flavors in the returned service."""
    if visibility == "public":
        mock_flavors.return_value = [
            FlavorCreateExtended(uuid=uuid4(), name=random_lower_string())
        ]
    elif visibility == "private":
        mock_flavors.return_value = [
            FlavorCreateExtended(
                uuid=uuid4(),
                name=random_lower_string(),
                is_public=False,
                projects=[openstack_item.project_conf.id],
            )
        ]
    elif visibility == "no-access":
        mock_flavors.return_value = []
    endpoint = random_url()
    mock_conn.compute.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_compute_service()
    if visibility == "no-access":
        assert len(item.flavors) == 0
    else:
        assert len(item.flavors) == 1


@parametrize_with_cases("visibility", cases=CaseResourceVisibility)
@patch("src.providers.openstack.OpenstackData.get_images")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_service_with_images(
    mock_conn: Mock,
    mock_images: Mock,
    openstack_item: OpenstackData,
    visibility: str,
) -> None:
    """Check images in the returned service."""
    if visibility == "public":
        mock_images.return_value = [
            ImageCreateExtended(uuid=uuid4(), name=random_lower_string())
        ]
    elif visibility == "private":
        mock_images.return_value = [
            ImageCreateExtended(
                uuid=uuid4(),
                name=random_lower_string(),
                is_public=False,
                projects=[openstack_item.project_conf.id],
            )
        ]
    elif visibility == "no-access":
        mock_images.return_value = []
    endpoint = random_url()
    mock_conn.compute.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_compute_service()
    if visibility == "no-access":
        assert len(item.images) == 0
    else:
        assert len(item.images) == 1


@parametrize_with_cases("tags", cases=CaseTagList)
@patch("src.providers.openstack.OpenstackData.get_images")
@patch("src.providers.openstack.Connection")
def test_retrieve_compute_service_images_tags(
    mock_conn: Mock,
    mock_images: Mock,
    openstack_item: OpenstackData,
    tags: list[str],
) -> None:
    """Check images in the returned service."""
    openstack_item.provider_conf.image_tags = tags
    mock_images.return_value = []
    endpoint = random_url()
    mock_conn.compute.get_endpoint.return_value = endpoint
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    item = openstack_item.get_compute_service()
    assert item is not None

    mock_images.assert_called_once_with(tags=openstack_item.provider_conf.image_tags)
