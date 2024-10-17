import os
from logging import getLogger
from typing import Literal
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ObjectStoreQuotaCreateExtended,
    ObjectStoreServiceCreateExtended,
)
from fed_reg.service.enum import ObjectStoreServiceName, ServiceType
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


@parametrize_with_cases("resp", cases=CaseEndpointResp)
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
def test_no_object_store_service(
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

    with patch("src.providers.openstack.Connection.object_store") as mock_srv:
        if resp:
            mock_srv.get_endpoint.side_effect = resp
        else:
            mock_srv.get_endpoint.return_value = resp
    mock_conn.object_store = mock_srv
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item.conn = mock_conn

    assert not item.get_object_store_service()

    mock_srv.get_endpoint.assert_called_once()


@patch("src.providers.openstack.OpenstackData.get_object_store_quotas")
@patch("src.providers.openstack.Connection.object_store")
@patch("src.providers.openstack.Connection")
@patch("src.providers.openstack.OpenstackData.retrieve_info")
@parametrize_with_cases("user_quota", cases=CaseUserQuotaPresence)
def test_retrieve_object_store_service_with_quotas(
    mock_retrieve_info: Mock,
    mock_conn: Mock,
    mock_object_store: Mock,
    mock_object_store_quotas: Mock,
    user_quota: bool,
    identity_provider_create: IdentityProviderCreateExtended,
) -> None:
    """Check quotas in the returned service."""
    per_user_limits = {"object_store": {"per_user": True}} if user_quota else {}
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
    mock_object_store_quotas.return_value = (
        ObjectStoreQuotaCreateExtended(project=project_conf.id),
        ObjectStoreQuotaCreateExtended(project=project_conf.id, usage=True),
    )
    mock_object_store.get_endpoint.return_value = os.path.join(endpoint, uuid4().hex)
    mock_conn.object_store = mock_object_store
    type(mock_conn).current_project_id = PropertyMock(return_value=uuid4().hex)
    item.conn = mock_conn

    item = item.get_object_store_service()
    assert isinstance(item, ObjectStoreServiceCreateExtended)
    assert item.description == ""
    assert item.endpoint == endpoint
    assert item.type == ServiceType.OBJECT_STORE.value
    assert item.name == ObjectStoreServiceName.OPENSTACK_SWIFT.value
    if user_quota:
        assert len(item.quotas) == 3
        assert item.quotas[2].per_user
    else:
        assert len(item.quotas) == 2
    assert not item.quotas[0].per_user
    assert item.quotas[1].usage
