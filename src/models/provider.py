from typing import List, Literal, Optional, Union

from app.auth_method.schemas import AuthMethodBase
from app.location.schemas import LocationBase
from app.models import BaseNode
from app.provider.enum import ProviderType
from app.provider.schemas import ProviderBase
from app.provider.schemas_extended import find_duplicates
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from app.region.schemas import RegionBase
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress, validator


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
    per_user_limits: Limits = Field(
        default_factory=Limits,
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
    per_user_limits: Limits = Field(
        default_factory=Limits,
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
    projects: List[Project] = Field(
        description="List of projects/namespaces... belonged by this provider"
    )

    @validator("identity_providers")
    @classmethod
    def find_idp_duplicates(cls, v: List[AuthMethod]) -> List[AuthMethod]:
        """Verify there are no duplicate authentication methods endpoints."""
        find_duplicates(v, "endpoint")
        find_duplicates(v, "idp_name")
        return v

    @validator("projects")
    @classmethod
    def find_proj_duplicates(cls, v: List[Project]) -> List[Project]:
        """Verify there are no duplicate project's IDs."""
        find_duplicates(v, "id")
        find_duplicates(v, "sla")
        return v

    @validator("regions")
    @classmethod
    def find_reg_duplicates(cls, v: List[Region]) -> List[Region]:
        """Verify there are no duplicate region names."""
        find_duplicates(v, "name")
        return v


class Openstack(Provider):
    type: ProviderType = Field(
        default=ProviderType.OS, description="Openstack provider type"
    )
    image_tags: List[str] = Field(
        default_factory=list, description="List of image tags to filter"
    )
    network_tags: List[str] = Field(
        default_factory=list, description="List of network tags to filter"
    )

    @validator("type")
    @classmethod
    def type_fixed(cls, v: Literal[ProviderType.OS]) -> Literal[ProviderType.OS]:
        assert v == ProviderType.OS
        return v

    @validator("regions", always=True)
    @classmethod
    def default_region(cls, v: List[Region]) -> List[Region]:
        if len(v) == 0:
            v.append(Region(name="RegionOne"))
        return v


class Kubernetes(Provider):
    type: ProviderType = Field(
        default=ProviderType.K8S, description="Kubernetes provider type"
    )

    @validator("type")
    @classmethod
    def type_fixed(cls, v: Literal[ProviderType.K8S]) -> Literal[ProviderType.K8S]:
        assert v == ProviderType.K8S
        return v

    @validator("regions", always=True)
    @classmethod
    def default_region(cls, v: List[Region]) -> List[Region]:
        if len(v) == 0:
            v.append(Region(name="default"))
        return v
