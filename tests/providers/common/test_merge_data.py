import copy
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    FlavorCreateExtended,
    IdentityProviderCreateExtended,
    ImageCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
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
    random_url,
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


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_merge_data_single_entry(
    provider_thread_item: ProviderThread,
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
):
    siblings = [(identity_provider_create, project_create, region_create)]
    identity_providers, projects, regions = provider_thread_item.merge_data(siblings)
    assert len(identity_providers) == 1
    assert isinstance(identity_providers[0], IdentityProviderCreateExtended)
    assert len(projects) == 1
    assert isinstance(projects[0], ProjectCreate)
    assert len(regions) == 1
    assert isinstance(regions[0], RegionCreateExtended)


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_merge_data_multi_entries(
    provider_thread_item: ProviderThread,
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
):
    idp2 = copy.deepcopy(identity_provider_create)
    idp2.endpoint = random_url()
    proj2 = copy.deepcopy(project_create)
    proj2.uuid = uuid4()
    reg2 = copy.deepcopy(region_create)
    reg2.name = random_lower_string()
    siblings = [
        (identity_provider_create, project_create, region_create),
        (idp2, proj2, reg2),
    ]
    identity_providers, projects, regions = provider_thread_item.merge_data(siblings)
    assert len(identity_providers) == 2
    assert len(projects) == 2
    assert len(regions) == 2


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_merge_data_multi_entries_to_merge(
    provider_thread_item: ProviderThread,
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
):
    idp2 = copy.deepcopy(identity_provider_create)
    proj2 = copy.deepcopy(project_create)
    reg2 = copy.deepcopy(region_create)
    siblings = [
        (identity_provider_create, project_create, region_create),
        (idp2, proj2, reg2),
    ]
    identity_providers, projects, regions = provider_thread_item.merge_data(siblings)
    assert len(identity_providers) == 1
    assert len(projects) == 1
    assert len(regions) == 1


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_merge_data_multi_entries_filter_projects(
    provider_thread_item: ProviderThread,
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
):
    region_create.compute_services[0].flavors.append(
        FlavorCreateExtended(
            name=random_lower_string(),
            uuid=uuid4(),
            is_public=False,
            projects=[project_create.uuid, uuid4()],
        )
    )
    region_create.compute_services[0].images.append(
        ImageCreateExtended(
            name=random_lower_string(),
            uuid=uuid4(),
            is_public=False,
            projects=[project_create.uuid, uuid4()],
        )
    )

    siblings = [(identity_provider_create, project_create, region_create)]
    items = provider_thread_item.merge_data(siblings)
    regions = items[2]
    assert len(regions) == 1
    assert len(regions[0].compute_services[0].flavors[0].projects) == 1
    assert len(regions[0].compute_services[0].images[0].projects) == 1
