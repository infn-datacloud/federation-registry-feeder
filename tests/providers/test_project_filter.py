from typing import Union
from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    ImageCreateExtended,
    ProjectCreate,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.providers.core import filter_projects_on_compute_service
from tests.schemas.utils import random_lower_string


class CaseResource:
    @parametrize(type=["flavor", "image"])
    @parametrize(projects=["empty", "exact_match", "one_match", "no_match"])
    def case_resource_projects(
        self,
        type: str,
        projects: str,
        project_create: ProjectCreate,
    ) -> Union[FlavorCreateExtended, ImageCreateExtended]:
        """Resource value description.

        Resource can be public (no projects).
        The resource projects can be an exact match of the target projects or the target
        projects can be a subset of the projects allowed the specific resource.

        Lists with no matches can't happen. See the func documentation for more details.
        """

        d = {"name": random_lower_string(), "uuid": uuid4()}
        if projects == "exact_match":
            d["is_public"] = False
            d["projects"] = [project_create.uuid]
        elif projects == "one_match":
            d["is_public"] = False
            d["projects"] = [project_create.uuid, uuid4().hex]

        if type == "flavor":
            return FlavorCreateExtended(**d)
        if type == "image":
            return ImageCreateExtended(**d)


@parametrize_with_cases("resource", cases=CaseResource)
def test_filter_projects(
    compute_service_create: ComputeServiceCreateExtended,
    project_create: ProjectCreate,
    resource: Union[FlavorCreateExtended, ImageCreateExtended],
) -> None:
    """
    None matching projects case can't exist since when retrieving resources we
    retrieve the ones accessible from the current project which is by construction
    one of the target projects.
    """
    target_projects = [project_create.uuid]
    if isinstance(resource, FlavorCreateExtended):
        compute_service_create.flavors = [resource]
    elif isinstance(resource, ImageCreateExtended):
        compute_service_create.images = [resource]
    filter_projects_on_compute_service(
        service=compute_service_create, include_projects=target_projects
    )

    updated_flavors = compute_service_create.flavors
    if len(updated_flavors) > 0:
        projects = len(updated_flavors[0].projects)
        target_len = min(len(target_projects), len(resource.projects))
        assert projects == target_len

    updated_images = compute_service_create.images
    if len(updated_images) > 0:
        projects = len(updated_images[0].projects)
        target_len = min(len(target_projects), len(resource.projects))
        assert projects == target_len
