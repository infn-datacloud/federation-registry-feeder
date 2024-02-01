from typing import Any, List, Literal, Tuple

import pytest
from app.provider.enum import ProviderType
from pytest_cases import parametrize, parametrize_with_cases

from src.models.config import SiteConfig
from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack


class CaseProviderType:
    def case_openstack(
        self, openstack_provider: Openstack
    ) -> Tuple[str, List[Openstack]]:
        return ProviderType.OS.value, [openstack_provider]

    def case_kubernetes(
        self, kubernetes_provider: Kubernetes
    ) -> Tuple[str, List[Kubernetes]]:
        return ProviderType.K8S.value, [kubernetes_provider]


class CaseInvalidAttr:
    @parametrize(attr=["trusted_idps", "openstack", "kubernetes"])
    def case_none(self, attr: str) -> Tuple[str, None]:
        return attr, None

    def case_single_issuer(
        self, issuer: Issuer
    ) -> Tuple[Literal["trusted_idps"], Issuer]:
        return "trusted_idps", issuer

    def case_single_openstack(
        self, openstack: Openstack
    ) -> Tuple[Literal["openstack"], Openstack]:
        return "openstack", openstack

    def case_single_kubernetes(
        self, kubernetes: Kubernetes
    ) -> Tuple[Literal["kubernetes"], Kubernetes]:
        return "kubernetes", kubernetes

    @parametrize(diff_attr=["endpoint", "idp_name"])
    def case_duplicated_issuers(
        self, diff_attr: str, issuer: Issuer
    ) -> Tuple[Literal["trusted_idps"], Issuer]:
        return "trusted_idps", [issuer, issuer]

    @parametrize(diff_attr=["id", "sla"])
    def case_duplicated_openstack(
        self, diff_attr: str, openstack: Openstack
    ) -> Tuple[Literal["openstack"], Openstack]:
        return "openstack", [openstack, openstack]

    def case_duplicated_kubernetes(
        self, kubernetes: Kubernetes
    ) -> Tuple[Literal["kubernetes"], Kubernetes]:
        return "kubernetes", [kubernetes, kubernetes]


@parametrize_with_cases("key, value", cases=CaseProviderType)
def test_site_config_schema(issuer: Issuer, key: str, value: Any) -> None:
    d = {"trusted_idps": [issuer]}
    d[key] = value
    item = SiteConfig(**d)
    assert item.trusted_idps == d.get("trusted_idps")
    assert item.openstack == d.get("openstack", [])
    assert item.kubernetes == d.get("kubernetes", [])


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_site_config_invalid_schema(issuer: Issuer, key: str, value: Any) -> None:
    d = {"trusted_idps": [issuer]}
    d[key] = value
    with pytest.raises(ValueError):
        SiteConfig(**d)
