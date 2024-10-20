from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    FlavorCreateExtended,
    ImageCreateExtended,
    NetworkCreateExtended,
)
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.core import ProviderThread
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
    sla_dict,
    user_group_dict,
)


class CaseProviderThread:
    def case_openstack(self) -> ProviderThread:
        provider = Openstack(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])

    def case_k8s(self) -> ProviderThread:
        provider = Kubernetes(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )
        issuer = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
        )
        return ProviderThread(provider_conf=provider, issuers=[issuer])


class CaseResources:
    def case_flavors(self) -> list[FlavorCreateExtended]:
        return [
            FlavorCreateExtended(name=random_lower_string(), uuid=uuid4()),
            FlavorCreateExtended(name=random_lower_string(), uuid=uuid4()),
            FlavorCreateExtended(name=random_lower_string(), uuid=uuid4()),
        ]

    def case_images(self) -> list[ImageCreateExtended]:
        return [
            ImageCreateExtended(name=random_lower_string(), uuid=uuid4()),
            ImageCreateExtended(name=random_lower_string(), uuid=uuid4()),
            ImageCreateExtended(name=random_lower_string(), uuid=uuid4()),
        ]

    def case_networks(self) -> list[NetworkCreateExtended]:
        return [
            NetworkCreateExtended(name=random_lower_string(), uuid=uuid4()),
            NetworkCreateExtended(name=random_lower_string(), uuid=uuid4()),
            NetworkCreateExtended(name=random_lower_string(), uuid=uuid4()),
        ]


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("resources", cases=CaseResources)
def test_identical_resources(
    provider_thread_item: ProviderThread,
    resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources[0:1]
    update_resources = provider_thread_item.get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 1


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("resources", cases=CaseResources)
def test_add_new_resources(
    provider_thread_item: ProviderThread,
    resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources[1:]
    update_resources = provider_thread_item.get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 3


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
@parametrize_with_cases("resources", cases=CaseResources)
def test_add_only_new_resources(
    provider_thread_item: ProviderThread,
    resources: list[FlavorCreateExtended]
    | list[ImageCreateExtended]
    | list[NetworkCreateExtended],
) -> None:
    curr_res = resources[0:1]
    new_res = resources
    update_resources = provider_thread_item.get_updated_resources(
        current_resources=curr_res, new_resources=new_res
    )
    assert len(update_resources) == 3
