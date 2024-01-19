from typing import List

from pydantic import BaseModel, Field

from src.models.identity_provider import TrustedIDP
from src.models.provider import Kubernetes, Openstack


class SiteConfig(BaseModel):
    trusted_idps: List[TrustedIDP] = Field(
        description="List of OIDC-Agent supported identity providers endpoints"
    )
    openstack: List[Openstack] = Field(
        default_factory=list,
        description="Openstack providers to integrate in the Federation Registry",
    )
    kubernetes: List[Kubernetes] = Field(
        default_factory=list,
        description="Kubernetes providers to integrate in the Federation Registry",
    )
