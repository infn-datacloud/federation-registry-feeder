from pydantic import AnyHttpUrl, BaseModel, Field


class URLs(BaseModel):
    flavors: AnyHttpUrl = Field(description="Flavors endpoint")
    identity_providers: AnyHttpUrl = Field(description="Identity Providers endpoint")
    images: AnyHttpUrl = Field(description="Images endpoint")
    locations: AnyHttpUrl = Field(description="Locations endpoint")
    networks: AnyHttpUrl = Field(description="Networks endpoint")
    projects: AnyHttpUrl = Field(description="Projects endpoint")
    providers: AnyHttpUrl = Field(description="Providers endpoint")
    regions: AnyHttpUrl = Field(description="Regions endpoint")
    quotas: AnyHttpUrl = Field(description="Quotas endpoint")
    services: AnyHttpUrl = Field(description="Services endpoint")
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
    regions: str = Field(default="v1", description="Regions API version to use")
    quotas: str = Field(default="v1", description="Quotas API version to use")
    services: str = Field(default="v1", description="Services API version to use")
    slas: str = Field(default="v1", description="SLAs API version to use")
    user_groups: str = Field(default="v1", description="User groups API version to use")


class FederationRegistry(BaseModel):
    base_url: AnyHttpUrl = Field(description="Federation Registry base URL")
    api_ver: APIVersions = Field(description="API versions")
