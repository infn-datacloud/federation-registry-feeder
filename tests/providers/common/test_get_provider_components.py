from unittest.mock import Mock, PropertyMock, patch

import pytest
from fed_reg.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ObjectStoreServiceCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
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
def test_get_openstack_components(
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

    components = item.get_provider_components()

    assert components is not None
    identity_provider, project, region = components
    assert isinstance(identity_provider, IdentityProviderCreateExtended)
    assert len(identity_provider.user_groups) == 1
    assert identity_provider.user_groups[0].name == issuer.user_groups[0].name
    assert (
        identity_provider.user_groups[0].sla.doc_uuid
        == issuer.user_groups[0].slas[0].doc_uuid
    )
    assert (
        identity_provider.user_groups[0].sla.start_date
        == issuer.user_groups[0].slas[0].start_date
    )
    assert (
        identity_provider.user_groups[0].sla.end_date
        == issuer.user_groups[0].slas[0].end_date
    )
    assert (
        identity_provider.user_groups[0].sla.project
        == issuer.user_groups[0].slas[0].projects[0]
    )
    assert isinstance(project, ProjectCreate)
    assert project == project_create
    assert isinstance(region, RegionCreateExtended)
    assert region.name == provider_conf.regions[0].name
    assert len(region.block_storage_services) > 0
    assert region.block_storage_services == [block_storage_service_create]
    assert len(region.compute_services) > 0
    assert region.compute_services == [compute_service_create]
    assert len(region.identity_services) > 0
    assert region.identity_services == [identity_service_create]
    assert len(region.network_services) > 0
    assert region.network_services == [network_service_create]
    assert len(region.object_store_services) > 0
    assert region.object_store_services == [s3_service_create]


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
            item.get_provider_components()


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
        item.get_provider_components()
