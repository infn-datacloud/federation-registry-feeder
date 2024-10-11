from logging import getLogger
from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityProviderCreateExtended,
    ImageCreateExtended,
)
from fed_reg.service.enum import ComputeServiceName, ServiceType
from keystoneauth1.exceptions.catalog import EndpointNotFound
from pytest_cases import parametrize_with_cases

from src.models.provider import Openstack, Project
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
    random_url,
)


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
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_no_compute_service(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    resp: EndpointNotFound | None,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """If the endpoint is not found or the service response is None, return None."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    with patch("src.providers.openstack.Connection.compute") as mock_srv:
        if resp:
            mock_srv.get_endpoint.side_effect = resp
        else:
            mock_srv.get_endpoint.return_value = resp
    mock_conn.compute = mock_srv
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    assert not item.get_compute_service()

    mock_srv.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_compute_quotas")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_compute_service_with_quotas(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_compute: Mock,
    mock_compute_quotas: Mock,
    user_quota: bool,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = {"compute": {"per_user": True}} if user_quota else {}
    project_conf = Project(**project_dict(), per_user_limits=per_user_limits)
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
    mock_compute_quotas.return_value = (
        ComputeQuotaCreateExtended(project=project_conf.id),
        ComputeQuotaCreateExtended(project=project_conf.id, usage=True),
    )
    mock_compute.get_endpoint.return_value = endpoint
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_compute_service()
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
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_compute_service_with_flavors(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_compute: Mock,
    mock_flavors: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
    visibility: str,
) -> None:
    """Check flavors in the returned service."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
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
                projects=[project_conf.id],
            )
        ]
    elif visibility == "no-access":
        mock_flavors.return_value = []
    mock_compute.get_endpoint.return_value = endpoint
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_compute_service()
    if visibility == "no-access":
        assert len(item.flavors) == 0
    else:
        assert len(item.flavors) == 1


@parametrize_with_cases("visibility", cases=CaseResourceVisibility)
@patch("src.providers.openstack.OpenstackData.get_images")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_compute_service_with_images(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_compute: Mock,
    mock_images: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
    visibility: str,
) -> None:
    """Check images in the returned service."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
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
                projects=[project_conf.id],
            )
        ]
    elif visibility == "no-access":
        mock_images.return_value = []
    mock_compute.get_endpoint.return_value = endpoint
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_compute_service()
    if visibility == "no-access":
        assert len(item.images) == 0
    else:
        assert len(item.images) == 1


@parametrize_with_cases("tags", cases=CaseTagList)
@patch("src.providers.openstack.OpenstackData.get_images")
@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_retrieve_compute_service_images_tags(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_compute: Mock,
    mock_images: Mock,
    identity_provider_create: IdentityProviderCreateExtended,
    tags: list[str],
) -> None:
    """Check images in the returned service."""
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
        image_tags=tags,
    )
    region_name = random_lower_string()
    logger = getLogger("test")
    token = random_lower_string()
    item = OpenstackData(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=identity_provider_create,
        region_name=region_name,
        token=token,
        logger=logger,
    )

    endpoint = random_url()
    image = ImageCreateExtended(uuid=uuid4(), name=random_lower_string())
    mock_images.return_value = [image]
    mock_compute.get_endpoint.return_value = endpoint
    mock_conn.compute = mock_compute
    type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
    item.conn = mock_conn

    item = item.get_compute_service()
    mock_images.assert_called_once_with(tags=provider_conf.image_tags)
