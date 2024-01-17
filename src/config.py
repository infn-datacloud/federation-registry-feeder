from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, BaseModel, BaseSettings, Field


class URLs(BaseModel):
    flavors: AnyHttpUrl = Field(description="Flavors endpoint")
    identity_providers: AnyHttpUrl = Field(description="Identity Providers endpoint")
    images: AnyHttpUrl = Field(description="Images endpoint")
    locations: AnyHttpUrl = Field(description="Locations endpoint")
    networks: AnyHttpUrl = Field(description="Networks endpoint")
    projects: AnyHttpUrl = Field(description="Projects endpoint")
    providers: AnyHttpUrl = Field(description="Providers endpoint")
    block_storage_quotas: AnyHttpUrl = Field(
        description="Block Storage Quotas endpoint"
    )
    compute_quotas: AnyHttpUrl = Field(description="Compute Quotas endpoint")
    network_quotas: AnyHttpUrl = Field(description="Network Quotas endpoint")
    regions: AnyHttpUrl = Field(description="Regions endpoint")
    block_storage_services: AnyHttpUrl = Field(
        description="Block Storage Services endpoint"
    )
    compute_services: AnyHttpUrl = Field(description="Compute Services endpoint")
    identity_services: AnyHttpUrl = Field(description="Identity Services endpoint")
    network_services: AnyHttpUrl = Field(description="Network Services endpoint")
    slas: AnyHttpUrl = Field(description="SLAs endpoint")
    user_groups: AnyHttpUrl = Field(description="User Groups endpoint")


class APIVersions(BaseSettings):
    FLAVORS: str = Field(default="v1", description="Flavors API version to use")
    IDENTITY_PROVIDERS: str = Field(
        default="v1", description="Identity providers API version to use"
    )
    IMAGES: str = Field(default="v1", description="Images API version to use")
    LOCATIONS: str = Field(default="v1", description="Locations API version to use")
    NETWORKS: str = Field(default="v1", description="Networks API version to use")
    PROJECTS: str = Field(default="v1", description="Projects API version to use")
    PROVIDERS: str = Field(default="v1", description="Providers API version to use")
    BLOCK_STORAGE_QUOTAS: str = Field(
        default="v1", description="Block Storage Quotas API version to use"
    )
    COMPUTE_QUOTAS: str = Field(
        default="v1", description="Compute Quotas API version to use"
    )
    NETWORK_QUOTAS: str = Field(
        default="v1", description="Network Quotas API version to use"
    )
    REGIONS: str = Field(default="v1", description="Regions API version to use")
    BLOCK_STORAGE_SERVICES: str = Field(
        default="v1", description="Block Storage Services API version to use"
    )
    COMPUTE_SERVICES: str = Field(
        default="v1", description="Compute Services API version to use"
    )
    IDENTITY_SERVICES: str = Field(
        default="v1", description="Identity Services API version to use"
    )
    NETWORK_SERVICES: str = Field(
        default="v1", description="Network Services API version to use"
    )
    SLAS: str = Field(default="v1", description="SLAs API version to use")
    USER_GROUPS: str = Field(default="v1", description="User groups API version to use")

    class Config:
        """Sub class to set attribute as case sensitive."""

        case_sensitive = True


class Settings(BaseSettings):
    FEDERATION_REGISTRY_URL: AnyHttpUrl = Field(
        default="http://localhost:8000", description="Federation Registry base URL"
    )
    BLOCK_STORAGE_VOL_LABELS: List[str] = Field(
        default_factory=list, description="List of accepted volume type labels."
    )
    PROVIDERS_CONF_DIR: str = Field(
        default="./providers-conf",
        description="Path to the directory containing the federated provider \
            yaml configurations.",
    )
    OIDC_AGENT_CONTAINER_NAME: str = Field(
        default="federation-registry-feeder-oidc-agent-1",
        description="Name of the container with the oidc-agent service instance.",
    )
    api_ver: APIVersions = Field(description="API versions.")

    class Config:
        """Sub class to set attribute as case sensitive."""

        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached settings."""
    return Settings(api_ver=APIVersions())
