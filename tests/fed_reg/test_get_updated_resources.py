from uuid import uuid4

from fedreg.provider.schemas_extended import (
    PrivateFlavorCreateExtended,
    PrivateImageCreateExtended,
    PrivateNetworkCreateExtended,
    SharedFlavorCreate,
    SharedImageCreate,
    SharedNetworkCreate,
)
from pytest_cases import case, parametrize_with_cases

from src.utils import get_updated_networks, get_updated_resources
from tests.utils import random_lower_string


class CaseResources:
    @case(tags="shared")
    def case_pub_flavors(self) -> list[SharedFlavorCreate]:
        return [
            SharedFlavorCreate(name=random_lower_string(), uuid=uuid4()),
            SharedFlavorCreate(name=random_lower_string(), uuid=uuid4()),
            SharedFlavorCreate(name=random_lower_string(), uuid=uuid4()),
        ]

    @case(tags="private")
    def case_priv_flavors(self) -> list[PrivateFlavorCreateExtended]:
        project1 = uuid4()
        project2 = uuid4()
        return [
            PrivateFlavorCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project1]
            ),
            PrivateFlavorCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project1]
            ),
            PrivateFlavorCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project2]
            ),
        ]

    @case(tags="shared")
    def case_pub_images(self) -> list[SharedImageCreate]:
        return [
            SharedImageCreate(name=random_lower_string(), uuid=uuid4()),
            SharedImageCreate(name=random_lower_string(), uuid=uuid4()),
            SharedImageCreate(name=random_lower_string(), uuid=uuid4()),
        ]

    @case(tags="private")
    def case_priv_images(self) -> list[PrivateImageCreateExtended]:
        project1 = uuid4()
        project2 = uuid4()
        return [
            PrivateImageCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project1]
            ),
            PrivateImageCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project1]
            ),
            PrivateImageCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project2]
            ),
        ]


class CaseNetworks:
    @case(tags="shared")
    def case_pub_networks(self) -> list[SharedNetworkCreate]:
        return [
            SharedNetworkCreate(name=random_lower_string(), uuid=uuid4()),
            SharedNetworkCreate(name=random_lower_string(), uuid=uuid4()),
            SharedNetworkCreate(name=random_lower_string(), uuid=uuid4()),
        ]

    @case(tags="private")
    def case_priv_networks(self) -> list[PrivateNetworkCreateExtended]:
        project1 = uuid4()
        project2 = uuid4()
        return [
            PrivateNetworkCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project1]
            ),
            PrivateNetworkCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project1]
            ),
            PrivateNetworkCreateExtended(
                name=random_lower_string(), uuid=uuid4(), projects=[project2]
            ),
        ]

    @case(tags="same-id-diff-proj")
    def case_same_net_diff_proj(self) -> list[PrivateNetworkCreateExtended]:
        net_id = uuid4()
        name = random_lower_string()
        project = uuid4()
        return [
            PrivateNetworkCreateExtended(
                name=name, uuid=net_id, projects=[project, uuid4()]
            ),
            PrivateNetworkCreateExtended(
                name=name, uuid=net_id, projects=[project, uuid4()]
            ),
        ]


@parametrize_with_cases("resources", cases=CaseResources)
def test_identical_resources(
    resources: list[SharedFlavorCreate]
    | list[PrivateFlavorCreateExtended]
    | list[SharedImageCreate]
    | list[PrivateImageCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources[0:1]
    update_resources = get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 1


@parametrize_with_cases("resources", cases=CaseResources)
def test_add_new_resources(
    resources: list[SharedFlavorCreate]
    | list[PrivateFlavorCreateExtended]
    | list[SharedImageCreate]
    | list[PrivateImageCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources[1:]
    update_resources = get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 3


@parametrize_with_cases("resources", cases=CaseResources)
def test_add_only_new_resources(
    resources: list[SharedFlavorCreate]
    | list[PrivateFlavorCreateExtended]
    | list[SharedImageCreate]
    | list[PrivateImageCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources
    update_resources = get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 3


@parametrize_with_cases("networks", cases=CaseNetworks, glob="*networks")
def test_identical_networks(
    networks: list[SharedNetworkCreate] | list[PrivateNetworkCreateExtended],
) -> None:
    curr_res = networks[0:1]
    new_res = networks[0:1]
    update_networks = get_updated_networks(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_networks) == 1
    if isinstance(update_networks[0], PrivateNetworkCreateExtended):
        assert len(update_networks[0].projects) == 1


@parametrize_with_cases("networks", cases=CaseNetworks, glob="*networks")
def test_add_new_networks(
    networks: list[SharedNetworkCreate] | list[PrivateNetworkCreateExtended],
) -> None:
    curr_res = networks[0:1]
    new_res = networks[1:]
    update_networks = get_updated_networks(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_networks) == 3


@parametrize_with_cases("networks", cases=CaseNetworks, glob="*networks")
def test_add_only_new_networks(
    networks: list[SharedNetworkCreate] | list[PrivateNetworkCreateExtended],
) -> None:
    curr_res = networks[0:1]
    new_res = networks
    update_networks = get_updated_networks(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_networks) == 3


@parametrize_with_cases("networks", cases=CaseNetworks, has_tag="same-id-diff-proj")
def test_update_only_network_projects(
    networks: list[SharedNetworkCreate] | list[PrivateNetworkCreateExtended],
) -> None:
    curr_res = networks[0:1]
    new_res = networks[1:]
    update_networks = get_updated_networks(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_networks) == 1
    assert len(update_networks[0].projects) == 3
