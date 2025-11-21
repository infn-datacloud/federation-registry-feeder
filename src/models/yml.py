"""Models and schemas to organize and validate data retrieved from YAML files."""

from typing import Annotated, Literal

from fed_mgr.v1.identity_providers.schemas import IdentityProviderBase
from fed_mgr.v1.identity_providers.user_groups.schemas import UserGroupBase
from fed_mgr.v1.identity_providers.user_groups.slas.schemas import SLABase
from fed_mgr.v1.providers.identity_providers.schemas import IdpOverridesBase
from fed_mgr.v1.providers.regions.schemas import RegionBase
from fed_mgr.v1.providers.schemas import ProviderBase, ProviderType
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BaseModel,
    Field,
    IPvAnyAddress,
    field_validator,
)

from src.utils import find_duplicates


class SLA(SLABase):
    """Model for Service level agreement."""

    name: Annotated[
        str | None, Field(default=None, alias="doc_uuid", description="Document UUID")
    ]
    url: Annotated[
        AnyHttpUrl | None, Field(default=None, description="Url of the object")
    ]
    projects: Annotated[
        list[str],
        Field(default_factory=list, description="list of projects UUID"),
        AfterValidator(find_duplicates),
    ]


class UserGroup(UserGroupBase):
    """Model for a user group."""

    slas: Annotated[list[SLA], Field(description="list of SLAs")]

    @field_validator("slas", mode="after")
    @classmethod
    def validate_slas(cls, v: list[SLA]) -> list[SLA]:
        """Find duplicates in list of SLAs.

        The matching key is "name".
        """
        find_duplicates(v, "name")
        return v


class IdentityProvider(IdpOverridesBase):
    """Model for an identity provider."""

    endpoint: Annotated[
        AnyHttpUrl, Field(alias="issuer", description="Identity provider issuer")
    ]
    user_groups: Annotated[list[UserGroup], Field(description="User groups")]

    @field_validator("user_groups")
    @classmethod
    def validate_user_groups(cls, v: list[UserGroup]) -> list[UserGroup]:
        """Verify the list is not empty and there are no duplicates."""
        find_duplicates(v, "name")
        if len(v) == 0:
            raise ValueError("Identity provider's user group list can't be empty")
        return v


class BlockStorageVolMap(BaseModel):
    """Model to map supported block storage volumes in standard QoS levels."""


class PrivateNetProxy(BaseModel):
    """Modelt to define the attributes of a PrivateNetProxy."""

    host: Annotated[
        str | IPvAnyAddress,
        Field(description="Proxy IP address or hostname with/without the port"),
    ]
    user: Annotated[
        str, Field(description="Username to use when performing ssh operations")
    ]


class PerRegionProps(BaseModel):
    """Model to define the projects overrides on a specific region."""

    region_name: Annotated[str, Field(description="Region name")]
    default_public_net: Annotated[
        str | None,
        Field(default=None, description="Name of the default public network"),
    ]
    default_private_net: Annotated[
        str | None,
        Field(default=None, description="Name of the default private network"),
    ]
    private_net_proxy: Annotated[
        PrivateNetProxy | None,
        Field(
            default=None,
            description="Proxy details to use to access to private network",
        ),
    ]


class Project(BaseModel):
    """Model for a Tenant/Namespace."""

    id: Annotated[str, Field(description="Project unique ID or name")]
    sla: Annotated[str, Field(description="SLA document uuid")]
    default_public_net: Annotated[
        str | None,
        Field(default=None, description="Name of the default public network"),
    ]
    default_private_net: Annotated[
        str | None,
        Field(default=None, description="Name of the default private network"),
    ]
    private_net_proxy: Annotated[
        PrivateNetProxy | None,
        Field(
            default=None,
            description="Proxy details to use to access to private network",
        ),
    ]
    per_region_props: Annotated[
        list[PerRegionProps],
        Field(default_factory=list, description="Region specific properties"),
    ]


class IDPConfig(IdentityProviderBase):
    """Model to define the resource provider's overrides on the idp attrs."""

    name: Annotated[str | None, Field(default=None, description="Useless in this case")]
    groups_claim: Annotated[
        str | None, Field(default=None, description="Useless in this case")
    ]


class Provider(ProviderBase):
    """Resource providers common attributes."""

    auth_endpoint: Annotated[
        AnyHttpUrl, Field(alias="auth_url", description="Identity service endpoint")
    ]
    block_storage_vol_types: Annotated[BlockStorageVolMap | None, Field(default=None)]
    identity_providers: Annotated[
        list[IDPConfig],
        Field(description="list of supported identity providers"),
    ]
    regions: Annotated[
        list[RegionBase],
        Field(default_factory=list, description="list of hosted regions"),
    ]
    projects: Annotated[
        list[Project],
        Field(description="list of projects/namespaces... belonged by this provider"),
    ]
    rally_username: Annotated[
        str | None,
        Field(
            default=None,
            description="It is not mandatory to define the rally user's name here",
        ),
    ]
    rally_password: Annotated[
        str | None,
        Field(
            default=None,
            description="It is not mandatory to define the rally user's password here",
        ),
    ]

    @field_validator("identity_providers")
    @classmethod
    def find_idp_duplicates(cls, v: list[IDPConfig]) -> list[IDPConfig]:
        """Verify there are no duplicate authentication methods endpoints."""
        find_duplicates(v, "endpoint")
        find_duplicates(v, "name")
        return v

    @field_validator("projects")
    @classmethod
    def find_proj_duplicates(cls, v: list[Project]) -> list[Project]:
        """Verify there are no duplicate project's IDs."""
        find_duplicates(v, "id")
        find_duplicates(v, "sla")
        return v

    @field_validator("regions")
    @classmethod
    def find_reg_duplicates(cls, v: list[RegionBase]) -> list[RegionBase]:
        """Verify there are no duplicate region names."""
        find_duplicates(v, "name")
        return v


class Openstack(Provider):
    """Model to define an openstack provider."""

    type: Annotated[
        Literal[ProviderType.openstack],
        Field(default=ProviderType.openstack, description="Openstack provider type"),
    ]
    image_tags: Annotated[
        list[str],
        Field(default_factory=list, description="list of image tags to filter"),
    ]
    network_tags: Annotated[
        list[str],
        Field(default_factory=list, description="list of network tags to filter"),
    ]
    regions: Annotated[
        list[RegionBase],
        Field(
            default_factory=lambda: [RegionBase(name="RegionOne")],
            description="list of hosted regions",
        ),
    ]


class Kubernetes(Provider):
    """Model to define an kubernetes provider."""

    type: Annotated[
        Literal[ProviderType.kubernetes],
        Field(default=ProviderType.kubernetes, description="Kubernetes provider type"),
    ]
    ca_fname: Annotated[
        str | None,
        Field(
            default=None,
            description="File name of the CA to use to connect to this cluster",
        ),
    ]
    regions: Annotated[
        list[RegionBase],
        Field(
            default_factory=lambda: [RegionBase(name="default")],
            description="list of hosted regions",
        ),
    ]


class YamlConfig(BaseModel):
    """Model to collect all the site configurations written in a YAML file."""

    trusted_idps: Annotated[
        list[IdentityProvider],
        Field(description="list of OIDC-Agent supported identity providers endpoints"),
    ]
    openstack: Annotated[
        list[Openstack],
        Field(
            default_factory=list,
            description="Openstack providers to integrate in the Federation-Registry",
        ),
    ]
    kubernetes: Annotated[
        list[Kubernetes],
        Field(
            default_factory=list,
            description="Kubernetes providers to integrate in the Federation-Registry",
        ),
    ]

    @field_validator("trusted_idps")
    @classmethod
    def validate_issuers(cls, v: list[IdentityProvider]) -> list[IdentityProvider]:
        """Verify the list is not empty and there are no duplicates."""
        find_duplicates(v, "endpoint")
        assert len(v), "Site config's Identity providers list can't be empty"
        return v

    @field_validator("openstack", "kubernetes")
    @classmethod
    def find_duplicates(cls, v: list[Provider]) -> list[Provider]:
        """Verify there are no duplicates."""
        find_duplicates(v, "name")
        return v
