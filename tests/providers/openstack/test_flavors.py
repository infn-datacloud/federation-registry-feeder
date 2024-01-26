from random import getrandbits, randint
from typing import Any, Dict, List
from unittest.mock import patch
from uuid import uuid4

import pytest
from openstack.compute.v2.flavor import Flavor
from pytest_cases import case, parametrize, parametrize_with_cases

from src.providers.openstack import get_flavors
from tests.schemas.utils import random_float, random_lower_string


def flavor_data() -> Dict[str, Any]:
    return {
        "name": random_lower_string(),
        "description": random_lower_string(),
        "disk": randint(0, 100),
        "is_public": getrandbits(1),
        "ram": randint(0, 100),
        "vcpus": randint(0, 100),
        "swap": randint(0, 100),
        "ephemeral": randint(0, 100),
        "is_disabled": False,
        "rxtx_factor": random_float(0, 100),
        "extra_specs": {},
    }


@case(tags=["public"])
@parametrize(public=[True, False])
def case_public(public: bool) -> bool:
    return public


@case(tags=["extra_specs"])
@parametrize(
    extra_specs=[
        "gpu_number",
        "aggregate_instance_extra_specs:local_storage",
        "infiniband",
    ]
)
def case_extra_specs(extra_specs: str) -> Dict[str, Any]:
    if extra_specs == "gpu_number":
        return {
            "gpu_number": randint(1, 100),
            "gpu_model": random_lower_string(),
            "gpu_vendor": random_lower_string(),
        }
    if extra_specs == "infiniband":
        return {extra_specs: getrandbits(1)}
    if extra_specs == "aggregate_instance_extra_specs:local_storage":
        return {extra_specs: random_lower_string()}


@pytest.fixture
def flavor_disabled() -> Flavor:
    d = flavor_data()
    d["is_disabled"] = True
    return Flavor(**d)


@pytest.fixture
@parametrize_with_cases("public", cases=".", has_tag="public")
def flavor_no_extra_specs(public: bool) -> Flavor:
    d = flavor_data()
    d["is_public"] = public
    return Flavor(**d)


@pytest.fixture
@parametrize_with_cases("extra_specs", cases=".", has_tag="extra_specs")
def flavor_with_extra_specs(extra_specs: Dict[str, Any]) -> Flavor:
    d = flavor_data()
    d["extra_specs"] = extra_specs
    return Flavor(**d)


@pytest.fixture
@parametrize(f=[flavor_disabled, flavor_with_extra_specs, flavor_no_extra_specs])
def flavor(f: Flavor) -> Flavor:
    return f


@patch("src.providers.openstack.Connection.compute")
@patch("src.providers.openstack.Connection")
def test_retrieve_flavors(mock_conn, mock_compute, flavor: Flavor) -> None:
    def get_allowed_project_ids(*args, **kwargs) -> List[Dict[str, str]]:
        return [{"tenant_id": uuid4().hex}]

    flavors = list(filter(lambda x: not x.is_disabled, [flavor]))
    mock_compute.flavors.return_value = flavors
    mock_compute.get_flavor_access.side_effect = get_allowed_project_ids
    mock_conn.compute = mock_compute
    data = get_flavors(mock_conn)

    assert len(data) == len(flavors)
    if len(data) > 0:
        item = data[0]
        assert item.description == flavor.description
        assert item.uuid == flavor.id
        assert item.name == flavor.name
        assert item.disk == flavor.disk
        assert item.is_public == flavor.is_public
        assert item.ram == flavor.ram
        assert item.vcpus == flavor.vcpus
        assert item.swap == flavor.swap
        assert item.ephemeral == flavor.ephemeral
        assert item.gpus == flavor.extra_specs.get("gpu_number", 0)
        assert item.gpu_model == flavor.extra_specs.get("gpu_model")
        assert item.gpu_vendor == flavor.extra_specs.get("gpu_vendor")
        assert item.local_storage == flavor.extra_specs.get(
            "aggregate_instance_extra_specs:local_storage"
        )
        assert item.infiniband == flavor.extra_specs.get("infiniband", False)
        if item.is_public:
            assert len(item.projects) == 0
        else:
            assert len(item.projects) == len(get_allowed_project_ids())
