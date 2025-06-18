from typing import Literal

from fedreg.v1.core import BaseNode
from fedreg.v1.location.schemas import LocationBase
from fedreg.v1.provider.enum import ProviderType
from fedreg.v1.provider.schemas import ProviderBase
from fedreg.v1.provider.schemas_extended import find_duplicates
from fedreg.v1.quota.schemas import (
    BlockStorageQuotaBase,
    ComputeQuotaBase,
    NetworkQuotaBase,
    ObjectStoreQuotaBase,
)
from fedreg.v1.region.schemas import RegionBase
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress, validator


class Limits(BaseNode):
    block_storage: BlockStorageQuotaBase | None = Field(
        default=None, description="Block storage per user quota"
    )
    compute: ComputeQuotaBase | None = Field(
        default=None, description="Compute per user quota"
    )
    network: NetworkQuotaBase | None = Field(
        default=None, description="Network per user quota"
    )
    object_store: ObjectStoreQuotaBase | None = Field(
        default=None, description="Object store per user quota"
    )

    @validator("*")
    @classmethod
    def set_per_user(
        cls,
        v: BlockStorageQuotaBase
        | ComputeQuotaBase
        | NetworkQuotaBase
        | ObjectStoreQuotaBase
        | None,
    ) -> (
        BlockStorageQuotaBase
        | ComputeQuotaBase
        | NetworkQuotaBase
        | ObjectStoreQuotaBase
        | None
    ):
        """These quotas applies to each user. Set per_user flag to true."""
        if v:
            v.per_user = True
        return v


class PrivateNetProxy(BaseNode):
    host: str | IPvAnyAddress = Field(
        description="Proxy IP address or Hostname. It is posible to define the port."
    )
    user: str = Field(description="Username to use when performing ssh operations")


class PerRegionProps(BaseNode):
    region_name: str = Field(description="Region name")
    default_public_net: str | None = Field(
        default=None, description="Name of the default public network"
    )
    default_private_net: str | None = Field(
        default=None, description="Name of the default private network"
    )
    private_net_proxy: PrivateNetProxy | None = Field(
        default=None, description="Proxy details to use to access to private network"
    )
    per_user_limits: Limits = Field(
        default_factory=Limits,
        description="Quota limitations to apply to users owning this project",
    )


class AuthMethod(BaseModel):
    endpoint: AnyHttpUrl = Field(description="Identity Provider URL")
    idp_name: str | None = Field(
        alias="name", description="Identity provider name used to authenticate"
    )
    protocol: str | None = Field(description="Protocol name")
    audience: str | None = Field(
        description="Audience to use when connecting to k8s clusters"
    )


class BlockStorageVolMap(BaseModel): ...


class Project(BaseNode):
    id: str = Field(description="Project unique ID or name")
    sla: str = Field(description="SLA document uuid")
    default_public_net: str | None = Field(
        default=None, description="Name of the default public network"
    )
    default_private_net: str | None = Field(
        default=None, description="Name of the default private network"
    )
    private_net_proxy: PrivateNetProxy | None = Field(
        default=None, description="Proxy details to use to access to private network"
    )
    per_user_limits: Limits = Field(
        default_factory=Limits,
        description="Quota limitations to apply to users owning this project",
    )
    per_region_props: list[PerRegionProps] = Field(
        default_factory=list, description="Region specific properties"
    )


class Region(RegionBase):
    location: LocationBase | None = Field(default=None, description="Location details")


class Provider(ProviderBase):
    auth_url: AnyHttpUrl = Field(description="Identity service endpoint")
    block_storage_vol_types: BlockStorageVolMap | None = Field(default=None)
    identity_providers: list[AuthMethod] = Field(
        description="list of supported identity providers"
    )
    regions: list[Region] = Field(
        default_factory=list, description="list of hosted regions"
    )
    projects: list[Project] = Field(
        description="list of projects/namespaces... belonged by this provider"
    )

    @validator("identity_providers")
    @classmethod
    def find_idp_duplicates(cls, v: list[AuthMethod]) -> list[AuthMethod]:
        """Verify there are no duplicate authentication methods endpoints."""
        find_duplicates(v, "endpoint")
        find_duplicates(v, "idp_name")
        return v

    @validator("projects")
    @classmethod
    def find_proj_duplicates(cls, v: list[Project]) -> list[Project]:
        """Verify there are no duplicate project's IDs."""
        find_duplicates(v, "id")
        find_duplicates(v, "sla")
        return v

    @validator("regions")
    @classmethod
    def find_reg_duplicates(cls, v: list[Region]) -> list[Region]:
        """Verify there are no duplicate region names."""
        find_duplicates(v, "name")
        return v


class Openstack(Provider):
    type: Literal[ProviderType.OS] = Field(
        default=ProviderType.OS, description="Openstack provider type"
    )
    image_tags: list[str] = Field(
        default_factory=list, description="list of image tags to filter"
    )
    network_tags: list[str] = Field(
        default_factory=list, description="list of network tags to filter"
    )

    @validator("regions", always=True)
    @classmethod
    def default_region(cls, regions: list[Region]) -> list[Region]:
        if len(regions) == 0:
            regions.append(Region(name="RegionOne"))
        return regions


class Kubernetes(Provider):
    type: Literal[ProviderType.K8S] = Field(
        default=ProviderType.K8S, description="Kubernetes provider type"
    )

    @validator("regions", always=True)
    @classmethod
    def default_region(cls, regions: list[Region]) -> list[Region]:
        if len(regions) == 0:
            regions.append(Region(name="default"))
        return regions
