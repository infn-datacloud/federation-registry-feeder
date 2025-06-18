from uuid import uuid4

from fedreg.v1.provider.schemas_extended import (
    ComputeServiceCreateExtended,
    PrivateFlavorCreateExtended,
    PrivateImageCreateExtended,
    ProjectCreate,
    SharedFlavorCreate,
    SharedImageCreate,
)
from pytest_cases import parametrize, parametrize_with_cases

from src.utils import filter_compute_resources_projects
from tests.utils import random_lower_string


class CaseResource:
    @parametrize(type=("flavor", "image"))
    @parametrize(projects=("empty", "exact_match", "one_match"))
    def case_resource(
        self,
        type: str,
        projects: str,
        project_create: ProjectCreate,
    ) -> (
        PrivateFlavorCreateExtended
        | SharedFlavorCreate
        | PrivateImageCreateExtended
        | SharedImageCreate
    ):
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
            d["projects"] = [project_create.uuid, uuid4()]
        else:
            # item is public.
            pass

        if type == "flavor":
            if d.get("projects", None):
                return PrivateFlavorCreateExtended(**d)
            else:
                return SharedFlavorCreate(**d)

        if type == "image":
            if d.get("projects", None):
                return PrivateImageCreateExtended(**d)
            else:
                return SharedImageCreate(**d)


@parametrize_with_cases("resource", cases=CaseResource)
def test_filter_projects(
    compute_service_create: ComputeServiceCreateExtended,
    project_create: ProjectCreate,
    resource: PrivateFlavorCreateExtended
    | SharedFlavorCreate
    | PrivateImageCreateExtended
    | SharedImageCreate,
) -> None:
    """
    None matching projects case can't exist since when retrieving resources we
    retrieve the ones accessible from the current project which is by construction
    one of the target projects.
    """
    target_projects = [project_create.uuid]
    if isinstance(resource, (PrivateFlavorCreateExtended, SharedFlavorCreate)):
        compute_service_create.flavors = [resource]
        updated_items = filter_compute_resources_projects(
            items=compute_service_create.flavors, projects=target_projects
        )
    elif isinstance(resource, (PrivateImageCreateExtended, SharedImageCreate)):
        compute_service_create.images = [resource]
        updated_items = filter_compute_resources_projects(
            items=compute_service_create.images, projects=target_projects
        )

    assert len(updated_items) == 1
    if isinstance(
        updated_items[0], (PrivateFlavorCreateExtended, PrivateImageCreateExtended)
    ):
        num_projects = len(updated_items[0].projects)
        target_len = min(len(target_projects), len(resource.projects))
        assert num_projects == target_len
