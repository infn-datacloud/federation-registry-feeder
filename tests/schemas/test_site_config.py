from typing import Any

import pytest
from fed_reg.provider.enum import ProviderType
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import AuthMethod, Kubernetes, Openstack, Project
from src.models.site_config import SiteConfig
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    project_dict,
    random_lower_string,
    random_url,
    sla_dict,
    user_group_dict,
)


class CaseProviderType:
    def case_openstack(self) -> tuple[str, list[Openstack]]:
        return ProviderType.OS.value, [
            Openstack(
                name=random_lower_string(),
                auth_url=random_url(),
                identity_providers=[AuthMethod(**auth_method_dict())],
                projects=[Project(**project_dict())],
            )
        ]

    def case_kubernetes(self) -> tuple[str, list[Kubernetes]]:
        return ProviderType.K8S.value, [
            Kubernetes(
                name=random_lower_string(),
                auth_url=random_url(),
                identity_providers=[AuthMethod(**auth_method_dict())],
                projects=[Project(**project_dict())],
            )
        ]


class CaseInvalidIssuers:
    def case_none(self) -> None:
        return None

    def case_empty_list(self) -> list:
        return []

    def case_single_instance(self) -> Issuer:
        return Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
        )

    def case_duplicated_endpoints(self) -> list[Issuer]:
        item1 = Issuer(
            **issuer_dict(),
            token=random_lower_string(),
            user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
        )
        item2 = Issuer(
            **{**issuer_dict(), "issuer": item1.endpoint},
            token=random_lower_string(),
            user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
        )
        return [item1, item2]


class CaseInvalidOpenstack:
    def case_none(self) -> None:
        return None

    def case_single_instance(self) -> Openstack:
        return Openstack(
            name=random_lower_string(),
            auth_url=random_url(),
            identity_providers=[AuthMethod(**auth_method_dict())],
            projects=[Project(**project_dict())],
        )

    def case_duplicated_instance(self) -> list[Openstack]:
        item1 = Openstack(
            name=random_lower_string(),
            auth_url=random_url(),
            identity_providers=[AuthMethod(**auth_method_dict())],
            projects=[Project(**project_dict())],
        )
        item2 = Openstack(
            name=item1.name,
            auth_url=random_url(),
            identity_providers=[AuthMethod(**auth_method_dict())],
            projects=[Project(**project_dict())],
        )
        return [item1, item2]


class CaseInvalidKubernetes:
    def case_none(self) -> None:
        return None

    def case_single_instance(self) -> Kubernetes:
        return Kubernetes(
            name=random_lower_string(),
            auth_url=random_url(),
            identity_providers=[AuthMethod(**auth_method_dict())],
            projects=[Project(**project_dict())],
        )

    def case_duplicated_instance(self) -> list[Kubernetes]:
        item1 = Kubernetes(
            name=random_lower_string(),
            auth_url=random_url(),
            identity_providers=[AuthMethod(**auth_method_dict())],
            projects=[Project(**project_dict())],
        )
        item2 = Kubernetes(
            name=item1.name,
            auth_url=random_url(),
            identity_providers=[AuthMethod(**auth_method_dict())],
            projects=[Project(**project_dict())],
        )
        return [item1, item2]


@parametrize_with_cases("key, value", cases=CaseProviderType)
def test_site_config_schema(key: str, value: Any) -> None:
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    d = {"trusted_idps": [issuer]}
    d[key] = value
    item = SiteConfig(**d)
    assert item.trusted_idps == d.get("trusted_idps")
    assert item.openstack == d.get("openstack", [])
    assert item.kubernetes == d.get("kubernetes", [])


@parametrize_with_cases("value", cases=CaseInvalidIssuers)
def test_site_config_invalid_issuers(value: Any) -> None:
    d = {"trusted_idps": value}
    with pytest.raises(ValueError):
        SiteConfig(**d)


@parametrize_with_cases("value", cases=CaseInvalidOpenstack)
def test_site_config_invalid_openstacks(value: Any) -> None:
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    d = {"trusted_idps": [issuer], "openstack": value}
    with pytest.raises(ValueError):
        SiteConfig(**d)


@parametrize_with_cases("value", cases=CaseInvalidKubernetes)
def test_site_config_invalid_kubernetes(value: Any) -> None:
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[UserGroup(**user_group_dict(), slas=[SLA(**sla_dict())])],
    )
    d = {"trusted_idps": [issuer], "kubernetes": value}
    with pytest.raises(ValueError):
        SiteConfig(**d)
