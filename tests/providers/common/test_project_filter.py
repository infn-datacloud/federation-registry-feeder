from uuid import uuid4

from fed_reg.provider.schemas_extended import (
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    ImageCreateExtended,
    ProjectCreate,
)
from pytest_cases import parametrize, parametrize_with_cases

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


class CaseResource:
    @parametrize(type=("flavor", "image"))
    @parametrize(projects=("empty", "exact_match", "one_match"))
    def case_resource(
        self,
        type: str,
        projects: str,
        project_create: ProjectCreate,
    ) -> FlavorCreateExtended | ImageCreateExtended:
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
            return FlavorCreateExtended(**d)
        if type == "image":
            return ImageCreateExtended(**d)


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
@parametrize_with_cases("resource", cases=CaseResource)
def test_filter_projects(
    compute_service_create: ComputeServiceCreateExtended,
    project_create: ProjectCreate,
    provider_thread_item: ProviderThread,
    resource: FlavorCreateExtended | ImageCreateExtended,
) -> None:
    """
    None matching projects case can't exist since when retrieving resources we
    retrieve the ones accessible from the current project which is by construction
    one of the target projects.
    """
    target_projects = [project_create.uuid]
    if isinstance(resource, FlavorCreateExtended):
        compute_service_create.flavors = [resource]
        updated_items = provider_thread_item.filter_compute_resources_projects(
            items=compute_service_create.flavors, projects=target_projects
        )
    elif isinstance(resource, ImageCreateExtended):
        compute_service_create.images = [resource]
        updated_items = provider_thread_item.filter_compute_resources_projects(
            items=compute_service_create.images, projects=target_projects
        )

    assert len(updated_items) == 1
    num_projects = len(updated_items[0].projects)
    target_len = min(len(target_projects), len(resource.projects))
    assert num_projects == target_len
