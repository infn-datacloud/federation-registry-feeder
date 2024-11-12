import copy
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    FlavorCreateExtended,
    IdentityProviderCreateExtended,
    ImageCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
)

from src.utils import merge_components
from tests.utils import random_lower_string, random_url


def test_merge_components_single_entry(
    identity_provider_create: IdentityProviderCreateExtended,
    project_create: ProjectCreate,
    region_create: RegionCreateExtended,
):
    siblings = [(identity_provider_create, project_create, region_create)]
    identity_providers, projects, regions = merge_components(siblings)
    assert len(identity_providers) == 1
    assert isinstance(identity_providers[0], IdentityProviderCreateExtended)
    assert len(projects) == 1
    assert isinstance(projects[0], ProjectCreate)
    assert len(regions) == 1
    assert isinstance(regions[0], RegionCreateExtended)


def test_merge_components_multi_entries(
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
    identity_providers, projects, regions = merge_components(siblings)
    assert len(identity_providers) == 2
    assert len(projects) == 2
    assert len(regions) == 2


def test_merge_components_multi_entries_to_merge(
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
    identity_providers, projects, regions = merge_components(siblings)
    assert len(identity_providers) == 1
    assert len(projects) == 1
    assert len(regions) == 1


def test_merge_components_multi_entries_filter_projects(
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
    items = merge_components(siblings)
    regions = items[2]
    assert len(regions) == 1
    assert len(regions[0].compute_services[0].flavors[0].projects) == 1
    assert len(regions[0].compute_services[0].images[0].projects) == 1
