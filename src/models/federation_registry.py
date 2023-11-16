from typing import List

from pydantic import AnyHttpUrl, BaseModel, Field


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


class APIVersions(BaseModel):
    flavors: str = Field(default="v1", description="Flavors API version to use")
    identity_providers: str = Field(
        default="v1", description="Identity providers API version to use"
    )
    images: str = Field(default="v1", description="Images API version to use")
    locations: str = Field(default="v1", description="Locations API version to use")
    networks: str = Field(default="v1", description="Networks API version to use")
    projects: str = Field(default="v1", description="Projects API version to use")
    providers: str = Field(default="v1", description="Providers API version to use")
    block_storage_quotas: str = Field(
        default="v1", description="Block Storage Quotas API version to use"
    )
    compute_quotas: str = Field(
        default="v1", description="Compute Quotas API version to use"
    )
    network_quotas: str = Field(
        default="v1", description="Network Quotas API version to use"
    )
    regions: str = Field(default="v1", description="Regions API version to use")
    block_storage_services: str = Field(
        default="v1", description="Block Storage Services API version to use"
    )
    compute_services: str = Field(
        default="v1", description="Compute Services API version to use"
    )
    identity_services: str = Field(
        default="v1", description="Identity Services API version to use"
    )
    network_ervices: str = Field(
        default="v1", description="Network Services API version to use"
    )
    slas: str = Field(default="v1", description="SLAs API version to use")
    user_groups: str = Field(default="v1", description="User groups API version to use")


class FederationRegistry(BaseModel):
    base_url: AnyHttpUrl = Field(description="Federation Registry base URL")
    api_ver: APIVersions = Field(description="API versions")
    block_storage_vol_labels: List[str] = Field(
        description="List of accepted volume type labels."
    )
