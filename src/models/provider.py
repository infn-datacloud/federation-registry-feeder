from typing import List, Optional, Union

from app.auth_method.schemas import AuthMethodBase
from app.location.schemas import LocationBase
from app.models import BaseNode
from app.provider.enum import ProviderType
from app.provider.schemas import ProviderBase
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from app.region.schemas import RegionBase
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress, validator

from src.models.identity_provider import TrustedIDP


class Limits(BaseNode):
    block_storage: Optional[BlockStorageQuotaBase] = Field(
        default=None, description="Block storage per user quota"
    )
    compute: Optional[ComputeQuotaBase] = Field(
        default=None, description="Compute per user quota"
    )
    network: Optional[NetworkQuotaBase] = Field(
        default=None, description="Network per user quota"
    )

    @validator("*")
    @classmethod
    def set_per_user(
        cls,
        v: Optional[Union[BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase]],
    ) -> Optional[Union[BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase]]:
        """These quotas applies to each user. Set per_user flag to true."""
        if v:
            v.per_user = True
        return v


class PrivateNetProxy(BaseNode):
    ip: IPvAnyAddress = Field(description="Proxy IP address")
    user: str = Field(description="Username to use when performing ssh operations")


class PerRegionProps(BaseNode):
    region_name: str = Field(description="Region name")
    default_public_net: Optional[str] = Field(
        default=None, description="Name of the default public network"
    )
    default_private_net: Optional[str] = Field(
        default=None, description="Name of the default private network"
    )
    private_net_proxy: Optional[PrivateNetProxy] = Field(
        default=None, description="Proxy details to use to access to private network"
    )
    per_user_limits: Optional[Limits] = Field(
        default=None,
        description="Quota limitations to apply to users owning this project",
    )


class AuthMethod(AuthMethodBase):
    idp_name: str = Field(
        alias="name", description="Identity provider name used to authenticate"
    )
    endpoint: AnyHttpUrl = Field(description="Identity Provider URL")


class BlockStorageVolMap(BaseModel):
    ...


class Project(BaseNode):
    id: str = Field(description="Project unique ID or name")
    sla: str = Field(description="SLA document uuid")
    default_public_net: Optional[str] = Field(
        default=None, description="Name of the default public network"
    )
    default_private_net: Optional[str] = Field(
        default=None, description="Name of the default private network"
    )
    private_net_proxy: Optional[PrivateNetProxy] = Field(
        default=None, description="Proxy details to use to access to private network"
    )
    per_user_limits: Optional[Limits] = Field(
        default=None,
        description="Quota limitations to apply to users owning this project",
    )
    per_region_props: List[PerRegionProps] = Field(
        default_factory=list, description="Region specific properties"
    )


class Region(RegionBase):
    location: Optional[LocationBase] = Field(
        default=None, description="Location details"
    )


class Provider(ProviderBase):
    auth_url: AnyHttpUrl = Field(description="Identity service endpoint")
    block_storage_vol_types: Optional[BlockStorageVolMap] = Field(default=None)
    identity_providers: List[AuthMethod] = Field(
        description="List of supported identity providers"
    )
    regions: List[Region] = Field(
        default_factory=list, description="List of hosted regions"
    )


class Openstack(Provider):
    type: ProviderType = Field(default="openstack", description="Provider type")
    projects: List[Project] = Field(
        description="List of Projects belonged by this provider"
    )
    image_tags: List[str] = Field(
        default_factory=list, description="List of image tags to filter"
    )
    network_tags: List[str] = Field(
        default_factory=list, description="List of network tags to filter"
    )

    @validator("type")
    def type_fixed(cls, v):
        assert v == ProviderType.OS
        return v

    @validator("regions")
    def default_region(cls, v):
        if len(v) == 0:
            v.append(Region(name="RegionOne"))
        return v


class Kubernetes(Provider):
    type: ProviderType = Field(default="kubernetes", description="Provider type")
    projects: List[Project] = Field(description="List of names")

    @validator("type")
    def type_fixed(cls, v):
        assert v == ProviderType.K8S
        return v

    @validator("regions")
    def default_region(cls, v):
        if len(v) == 0:
            v.append(Region(name="default"))
        return v


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
        description="Openstack providers to integrate in the Federation Registry",
    )
