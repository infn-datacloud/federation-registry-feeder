from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING

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


class CaseProvider:
    def case_openstack(self) -> Openstack:
        return Openstack(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )

    def case_k8s(self) -> Kubernetes:
        return Kubernetes(
            **openstack_dict(),
            identity_providers=[auth_method_dict()],
            projects=[project_dict()],
        )


class CaseLogLevels:
    def case_none(self) -> None:
        return None

    @parametrize(level=(DEBUG, INFO, WARNING, ERROR, CRITICAL))
    def case_level(self, level: int) -> int:
        return level


@parametrize_with_cases("provider", cases=CaseProvider)
@parametrize_with_cases("level", cases=CaseLogLevels)
def test_provider_thread_creation(provider: Openstack | Kubernetes, level: int | None):
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [sla_dict()]}],
    )
    item = ProviderThread(provider_conf=provider, issuers=[issuer], log_level=level)
    assert item.provider_conf == provider
    assert len(item.issuers) == 1
    assert item.issuers[0] == issuer
    assert item.log_level == level
    assert item.logger is not None
    assert item.logger.level == (level if level is not None else NOTSET)
    assert item.logger.name == f"Provider {provider.name}"
    assert not item.error
