from unittest.mock import Mock, PropertyMock, patch

import pytest
from fedreg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
)
from keystoneauth1.exceptions.connection import ConnectFailure
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.conn_thread import ConnectionThread
from src.providers.openstack import OpenstackProviderError
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    kubernetes_dict,
    openstack_dict,
    project_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string


class CaseError:
    def case_openstack_provider_error(self) -> OpenstackProviderError:
        return OpenstackProviderError()

    def case_connect_failure(self) -> ConnectFailure:
        return ConnectFailure()


@patch("src.providers.conn_thread.OpenstackData")
def test_get_openstack_data(
    mock_openstack_data: Mock,
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    identity_service_create: IdentityServiceCreate,
    network_service_create: NetworkServiceCreateExtended,
    s3_service_create: ObjectStoreServiceCreateExtended,
):
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[
            {
                **user_group_dict(),
                "slas": [{**sla_dict(), "projects": [provider_conf.projects[0].id]}],
            }
        ],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint
    item = ConnectionThread(provider_conf=provider_conf, issuer=issuer)

    type(mock_openstack_data()).project = PropertyMock(return_value=project_create)
    type(mock_openstack_data()).block_storage_services = PropertyMock(
        return_value=[block_storage_service_create]
    )
    type(mock_openstack_data()).compute_services = PropertyMock(
        return_value=[compute_service_create]
    )
    type(mock_openstack_data()).identity_services = PropertyMock(
        return_value=[identity_service_create]
    )
    type(mock_openstack_data()).network_services = PropertyMock(
        return_value=[network_service_create]
    )
    type(mock_openstack_data()).object_store_services = PropertyMock(
        return_value=[s3_service_create]
    )

    data = item.get_provider_data()

    assert data is not None
    assert data.project == type(mock_openstack_data()).project
    assert (
        data.block_storage_services
        == type(mock_openstack_data()).block_storage_services
    )
    assert data.compute_services == type(mock_openstack_data()).compute_services
    assert data.identity_services == type(mock_openstack_data()).identity_services
    assert data.network_services == type(mock_openstack_data()).network_services
    assert (
        data.object_store_services == type(mock_openstack_data()).object_store_services
    )


@parametrize_with_cases("error", cases=CaseError)
def test_openstack_raise_error(error: OpenstackProviderError | ConnectFailure):
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[
            {
                **user_group_dict(),
                "slas": [{**sla_dict(), "projects": [provider_conf.projects[0].id]}],
            }
        ],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint
    item = ConnectionThread(provider_conf=provider_conf, issuer=issuer)

    with patch(
        "src.providers.conn_thread.OpenstackData",
        side_effect=error,
    ):
        with pytest.raises(type(error)):
            item.get_provider_data()


def test_get_kubernetes_components():
    provider_conf = Kubernetes(
        **kubernetes_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[
            {
                **user_group_dict(),
                "slas": [{**sla_dict(), "projects": [provider_conf.projects[0].id]}],
            }
        ],
    )
    issuer.endpoint = provider_conf.identity_providers[0].endpoint
    item = ConnectionThread(provider_conf=provider_conf, issuer=issuer)

    with pytest.raises(NotImplementedError):
        item.get_provider_data()
