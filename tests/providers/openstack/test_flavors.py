from random import getrandbits, randint
from typing import Any
from unittest.mock import Mock, PropertyMock, patch

from fed_reg.provider.schemas_extended import FlavorCreateExtended
from openstack.compute.v2.flavor import Flavor
from openstack.exceptions import ForbiddenException
from pytest_cases import case, parametrize, parametrize_with_cases

from src.providers.openstack import OpenstackData
from tests.providers.openstack.utils import openstack_flavor_dict
from tests.utils import random_lower_string


class CaseExtraSpecs:
    @parametrize(second_attr=["gpu_model", "gpu_vendor"])
    def case_gpu(self, second_attr: str) -> dict[str, Any]:
        return {"gpu_number": randint(1, 100), second_attr: random_lower_string()}

    def case_infiniband(self) -> dict[str, Any]:
        return {"infiniband": getrandbits(1)}

    def case_local_storage(self) -> dict[str, Any]:
        return {"aggregate_instance_extra_specs:local_storage": random_lower_string()}


class CaseOpenstackFlavor:
    def case_basic(self) -> Flavor:
        """Fixture with enabled flavor."""
        return Flavor(**openstack_flavor_dict())

    def case_flavor_disabled(self) -> Flavor:
        """Fixture with disabled flavor."""
        d = openstack_flavor_dict()
        d["is_disabled"] = True
        return Flavor(**d)

    def case_flavor_with_desc(self) -> Flavor:
        """Fixture with a flavor with description."""
        d = openstack_flavor_dict()
        d["description"] = random_lower_string()
        return Flavor(**d)

    @case(tags="private")
    def case_flavor_private(self) -> Flavor:
        """Fixture with private flavor."""
        d = openstack_flavor_dict()
        d["is_public"] = False
        return Flavor(**d)

    @parametrize_with_cases("extra_specs", cases=CaseExtraSpecs)
    def case_flavor_with_extra_specs(self, extra_specs: dict[str, Any]) -> Flavor:
        """Fixture with a flavor with extra specs."""
        d = openstack_flavor_dict()
        d["extra_specs"] = extra_specs
        return Flavor(**d)


@patch("src.providers.openstack.Connection")
@parametrize_with_cases("openstack_flavor", cases=CaseOpenstackFlavor)
def test_retrieve_flavors(
    mock_conn: Mock, openstack_flavor: Flavor, openstack_item: OpenstackData
) -> None:
    """Successful retrieval of a flavors.

    Retrieve only active flavors.

    Flavors retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    flavors = list(filter(lambda x: not x.is_disabled, [openstack_flavor]))
    mock_conn.compute.get_flavor_access.return_value = [
        {"tenant_id": openstack_item.project_conf.id}
    ]
    mock_conn.compute.flavors.return_value = flavors
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_flavors()
    assert len(data) == len(flavors)
    if len(data) > 0:
        item = data[0]
        assert isinstance(item, FlavorCreateExtended)
        if openstack_flavor.description:
            assert item.description == openstack_flavor.description
        else:
            assert item.description == ""
        assert item.uuid == openstack_flavor.id
        assert item.name == openstack_flavor.name
        assert item.disk == openstack_flavor.disk
        assert item.is_public == openstack_flavor.is_public
        assert item.ram == openstack_flavor.ram
        assert item.vcpus == openstack_flavor.vcpus
        assert item.swap == openstack_flavor.swap
        assert item.ephemeral == openstack_flavor.ephemeral
        assert item.gpus == openstack_flavor.extra_specs.get("gpu_number", 0)
        assert item.gpu_model == openstack_flavor.extra_specs.get("gpu_model")
        assert item.gpu_vendor == openstack_flavor.extra_specs.get("gpu_vendor")
        assert item.local_storage == openstack_flavor.extra_specs.get(
            "aggregate_instance_extra_specs:local_storage"
        )
        assert item.infiniband == openstack_flavor.extra_specs.get("infiniband", False)
        if item.is_public:
            assert len(item.projects) == 0
        else:
            assert len(item.projects) == 1


@parametrize_with_cases("extra_specs", cases=CaseExtraSpecs)
def test_retrieve_flavor_extra_specs(
    extra_specs: dict[str, Any], openstack_item: OpenstackData
) -> None:
    """Successful retrieval of a flavors.

    Retrieve only active flavors.

    Flavors retrieval fail is not tested here. It is tested where the exception is
    caught: get_data_from_openstack function.
    """
    data = openstack_item.get_flavor_extra_specs(extra_specs)
    assert data.get("gpus") == extra_specs.get("gpu_number", 0)
    assert data.get("gpu_model") == extra_specs.get("gpu_model")
    assert data.get("gpu_vendor") == extra_specs.get("gpu_vendor")
    assert data.get("local_storage") == extra_specs.get(
        "aggregate_instance_extra_specs:local_storage"
    )
    assert data.get("infiniband") == extra_specs.get("infiniband", False)


@patch("src.providers.openstack.Connection")
@parametrize_with_cases(
    "openstack_flavor", cases=CaseOpenstackFlavor, has_tag="private"
)
def test_retrieve_private_flavor_projects(
    mock_conn: Mock, openstack_flavor: Flavor, openstack_item: OpenstackData
) -> None:
    """ """
    mock_conn.compute.get_flavor_access.return_value = [
        {"tenant_id": openstack_item.project_conf.id}
    ]
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_flavor_projects(openstack_flavor)
    assert len(data) == 1
    assert data[0] == openstack_item.project_conf.id


@patch("src.providers.openstack.Connection")
@parametrize_with_cases(
    "openstack_flavor", cases=CaseOpenstackFlavor, has_tag="private"
)
def test_catch_forbidden_exception_when_reading_flavor_projects(
    mock_conn: Mock, openstack_flavor: Flavor, openstack_item: OpenstackData
) -> None:
    """
    Catch ForbiddenException and filter out private flavors if the openstack policy does
    not allow to read os-flavor-access.
    """
    mock_conn.compute.get_flavor_access.side_effect = ForbiddenException()
    type(mock_conn).current_project_id = PropertyMock(
        return_value=openstack_item.project_conf.id
    )
    openstack_item.conn = mock_conn

    data = openstack_item.get_flavor_projects(openstack_flavor)
    assert len(data) == 0
    assert openstack_item.error


# This case should neve happen
# @patch("src.providers.openstack.Connection.compute.get_flavor_access")
# @patch("src.providers.openstack.Connection.compute")
# @patch("src.providers.openstack.Connection")
# @parametrize_with_cases(
#     "openstack_flavor", cases=CaseOpenstackFlavor, has_tag="private"
# )
# def test_no_matching_project_id_when_retrieving_private_flavor(
#     mock_conn: Mock,
#     mock_compute: Mock,
#     mock_flavor_access: Mock,
#     openstack_flavor: Flavor,
#     openstack_item: OpenstackData
# ) -> None:
#     """
#     Filter out private flavors not visible to the current project.
#     """
#     project_conf = Project(**project_dict())
#     provider_conf = Openstack(
#         **openstack_dict(),
#         identity_providers=[auth_method_dict()],
#         projects=[project_conf],
#     )
#     region_name = random_lower_string()
#     logger = getLogger("test")
#     token = random_lower_string()
#     item = OpenstackData(
#         provider_conf=provider_conf,
#         project_conf=project_conf,
#         identity_provider=identity_provider_create,
#         region_name=region_name,
#         token=token,
#         logger=logger,
#     )

#     flavors = list(filter(lambda x: not x.is_disabled, [openstack_flavor]))
#     mock_flavor_access.return_value = [{"tenant_id": uuid4().hex}]
#     mock_compute.flavors.return_value = flavors
#     mock_conn.compute = mock_compute
#     type(mock_conn).current_project_id = PropertyMock(return_value=project_conf.id)
#     item.conn = mock_conn

#     data = item.get_flavors()
#     assert len(data) == 0
