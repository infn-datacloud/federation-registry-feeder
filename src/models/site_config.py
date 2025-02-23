from fedreg.provider.schemas_extended import find_duplicates
from pydantic import BaseModel, Field, validator

from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack, Provider


class SiteConfig(BaseModel):
    trusted_idps: list[Issuer] = Field(
        description="list of OIDC-Agent supported identity providers endpoints"
    )
    openstack: list[Openstack] = Field(
        default_factory=list,
        description="Openstack providers to integrate in the Federation-Registry",
    )
    kubernetes: list[Kubernetes] = Field(
        default_factory=list,
        description="Kubernetes providers to integrate in the Federation-Registry",
    )

    @validator("trusted_idps")
    @classmethod
    def validate_issuers(cls, v: list[Issuer]) -> list[Issuer]:
        """Verify the list is not empty and there are no duplicates."""
        find_duplicates(v, "endpoint")
        assert len(v), "Site config's Identity providers list can't be empty"
        return v

    @validator("openstack", "kubernetes")
    @classmethod
    def find_duplicates(cls, v: list[Provider]) -> list[Provider]:
        """Verify there are no duplicates."""
        find_duplicates(v, "name")
        return v
