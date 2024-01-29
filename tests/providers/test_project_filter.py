from uuid import uuid4

from app.provider.schemas_extended import (
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    ImageCreateExtended,
)
from pytest_cases import case, parametrize, parametrize_with_cases

from src.providers.core import filter_projects_on_compute_service
from tests.schemas.utils import (
    random_compute_service_name,
    random_lower_string,
    random_url,
)


@case(tags=["type"])
@parametrize(resource=["flavor", "image"])
def case_res_type(resource: str) -> str:
    return resource


@case(tags=["value"])
@parametrize(resource=["public", "exact_match", "one_match"])
def case_resource(resource: str) -> str:
    """Resource value description.

    Resource can be public (no projects).
    The resource projects can be an exact match of
    the target projects or the target projects can be a subset of the projects allowed
    the specific resource.
    None matching projects case can't exist since when retrieving resources we retrieve
    the ones accessible from the current project which is by construction one of the
    target projects.
    """
    return resource


@parametrize_with_cases("res_type", cases=".", has_tag="type")
@parametrize_with_cases("res_val", cases=".", has_tag="value")
def test_filter_projects(res_type: str, res_val: str) -> None:
    target_projects = [uuid4().hex]
    flavors = []
    images = []
    if res_type == "flavor" and res_val == "public":
        flavors = [FlavorCreateExtended(name=random_lower_string(), uuid=uuid4())]
    elif res_type == "flavor" and res_val == "exact_match":
        flavors = [
            FlavorCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=target_projects,
            )
        ]
    elif res_type == "flavor" and res_val == "one_match":
        flavors = [
            FlavorCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=[*target_projects, uuid4().hex],
            )
        ]
    elif res_type == "image" and res_val == "public":
        images = [ImageCreateExtended(name=random_lower_string(), uuid=uuid4())]
    elif res_type == "image" and res_val == "exact_match":
        images = [
            ImageCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=target_projects,
            )
        ]
    elif res_type == "image" and res_val == "one_match":
        images = [
            ImageCreateExtended(
                name=random_lower_string(),
                uuid=uuid4(),
                is_public=False,
                projects=[*target_projects, uuid4()],
            )
        ]
    compute_service = ComputeServiceCreateExtended(
        endpoint=random_url(),
        name=random_compute_service_name(),
        flavors=flavors,
        images=images,
    )
    filter_projects_on_compute_service(
        service=compute_service, include_projects=target_projects
    )

    updated_flavors = compute_service.flavors
    if len(updated_flavors) > 0:
        projects = len(updated_flavors[0].projects)
        target_len = min(len(target_projects), len(flavors[0].projects))
        assert projects == target_len

    updated_images = compute_service.images
    if len(updated_images) > 0:
        projects = len(updated_images[0].projects)
        target_len = min(len(target_projects), len(images[0].projects))
        assert projects == target_len
