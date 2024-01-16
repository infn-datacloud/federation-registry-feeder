import subprocess
from typing import Any, List, Optional, Union
from uuid import UUID

from app.auth_method.schemas import AuthMethodBase
from app.identity_provider.schemas import IdentityProviderBase
from app.location.schemas import LocationBase
from app.provider.enum import ProviderType
from app.provider.schemas import ProviderBase
from app.provider.schemas_extended import find_duplicates
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from app.region.schemas import RegionBase
from app.sla.schemas import SLABase
from app.user_group.schemas import UserGroupBase
from config import get_settings
from pydantic import AnyHttpUrl, BaseModel, Field, root_validator, validator


class SLA(SLABase):
    projects: List[str] = Field(
        default_factory=list, description="List of projects UUID"
    )

    @validator("projects", pre=True)
    def validate_projects(cls, v):
        v = [i.hex if isinstance(i, UUID) else i for i in v]
        find_duplicates(v)
        return v

    @root_validator
    def start_date_before_end_date(cls, values):
        start = values.get("start_date")
        end = values.get("end_date")
        assert start < end, f"Start date {start} greater than end date {end}"
        return values


class UserGroup(UserGroupBase):
    slas: List[SLA] = Field(default_factory=list, description="List of SLAs")

    @validator("slas")
    def validate_slas(cls, v):
        find_duplicates(v, "doc_uuid")
        assert len(v), "SLA list can't be empty"
        return v


class TrustedIDP(IdentityProviderBase):
    endpoint: AnyHttpUrl = Field(description="issuer url", alias="issuer")
    token: Optional[str] = Field(description="Access token")
    user_groups: List[UserGroup] = Field(
        default_factory=list, description="User groups"
    )
    relationship: Optional[AuthMethodBase] = Field(default=None, description="")

    @validator("token", pre=True, always=True)
    def get_token(cls, v, values):
        # Generate token
        if not v:
            settings = get_settings()
            token_cmd = subprocess.run(
                [
                    "docker",
                    "exec",
                    settings.OIDC_AGENT_CONTAINER_NAME,
                    "oidc-token",
                    values.get("endpoint"),
                ],
                capture_output=True,
                text=True,
            )
            v = token_cmd.stdout.strip("\n")
            if token_cmd.stderr:
                raise ValueError(token_cmd.stderr)
        return v


class Limits(BaseModel):
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
    def set_per_user(
        cls,
        v: Optional[Union[BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase]],
    ) -> Optional[Union[BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase]]:
        """These quotas applies to each user. Set per_user flag to true."""
        if v:
            v.per_user = True
        return v


class PrivateNetProxy(BaseModel):
    ip: str = Field(description="Proxy IP address")
    user: str = Field(description="Username to use when performing ssh operations")


class PerRegionProps(BaseModel):
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


class Project(BaseModel):
    id: str = Field(default=None, description="Project unique ID or name")
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
    sla: str = Field(description="SLA document uuid")

    @validator("*", pre=True)
    @classmethod
    def get_str_from_uuid(cls, v: Any) -> Any:
        """Get hex attribute from UUID values."""
        return v.hex if isinstance(v, UUID) else v


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
