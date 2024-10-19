from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack, PerRegionProps, Project
from src.providers.core import ProviderThread
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    private_net_proxy_dict,
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


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_prepare_project_conf(provider_thread_item: ProviderThread) -> None:
    provider_thread_item.provider_conf.projects[0].per_region_props = [
        PerRegionProps(
            region_name=provider_thread_item.provider_conf.regions[0].name,
            default_private_net=random_lower_string(),
            default_public_net=random_lower_string(),
            private_net_proxy=private_net_proxy_dict(),
            per_user_limits={},
        )
    ]
    project = provider_thread_item.provider_conf.projects[0]
    region_name = provider_thread_item.provider_conf.regions[0].name
    item = provider_thread_item.prepare_project_conf(
        project=project, region_name=region_name
    )
    assert item is not None
    assert isinstance(item, Project)
    assert item.description == project.description
    assert item.id == project.id
    assert item.sla == project.sla
    assert item.default_private_net == project.per_region_props[0].default_private_net
    assert item.default_public_net == project.per_region_props[0].default_public_net
    assert item.private_net_proxy == project.per_region_props[0].private_net_proxy
    assert item.per_user_limits == project.per_region_props[0].per_user_limits
    assert len(item.per_region_props) == 0


@parametrize_with_cases("provider_thread_item", cases=CaseProviderThread)
def test_prepare_project_conf_no_matching_region(
    provider_thread_item: ProviderThread,
) -> None:
    provider_thread_item.provider_conf.projects[0].per_region_props = [
        PerRegionProps(
            region_name=provider_thread_item.provider_conf.regions[0].name,
            default_private_net=random_lower_string(),
            default_public_net=random_lower_string(),
            private_net_proxy=private_net_proxy_dict(),
            per_user_limits={},
        )
    ]
    project = provider_thread_item.provider_conf.projects[0]
    item = provider_thread_item.prepare_project_conf(
        project=project, region_name=random_lower_string()
    )
    assert item is not None
    assert isinstance(item, Project)
    assert item.description == project.description
    assert item.id == project.id
    assert item.sla == project.sla
    assert item.default_private_net == project.default_private_net
    assert item.default_public_net == project.default_public_net
    assert item.private_net_proxy == project.private_net_proxy
    assert item.per_user_limits == project.per_user_limits
    assert len(item.per_region_props) == 0
