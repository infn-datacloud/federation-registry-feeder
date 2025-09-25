"""Models to define sites configurations."""

from typing import Annotated

from fed_mgr.v1.providers.schemas import ProviderType
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress


class SiteConfig(BaseModel):
    """Model to define all the data needed to connect to a resource provider.

    Not all data contained in this class are used to open the connection with the
    provider but they must be sent to kafka.
    """

    provider_name: Annotated[str, Field(description="Provider name")]
    provider_type: Annotated[ProviderType, Field(description="Provider type")]
    provider_endpoint: Annotated[AnyHttpUrl, Field(description="Connection URL")]
    region_name: Annotated[str, Field(description="Name of the region")]
    project_id: Annotated[str, Field(description="ID of the tenant or namespace")]
    idp_endpoint: Annotated[AnyHttpUrl, Field(description="Identity provider's issuer")]
    idp_protocol: Annotated[
        str | None,
        Field(default=None, description="Protocol name used by the provider"),
    ]
    idp_name: Annotated[
        str | None,
        Field(
            default=None,
            description="Name of the IDP stored in the provider configuration",
        ),
    ]
    idp_audience: Annotated[
        str | None, Field(default=None, description="Audience needed in the token")
    ]
    idp_token: Annotated[
        str | None,
        Field(
            default=None,
            description="OIDC token of the service user on the specified idp to be use "
            "to connect to the provider",
        ),
    ]
    user_group: Annotated[str, Field(description="Authorized user group")]
    image_tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="List of tags used to filter provider images (used only with "
            "'openstack' provider types)",
        ),
    ]
    network_tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="List of tags used to filter provider networks (used only with "
            "'openstack' provider types)",
        ),
    ]
    overbooking_cpu: Annotated[
        float, Field(default=1, description="Value used to overbook RAM.")
    ]
    overbooking_ram: Annotated[
        float, Field(default=1, description="Value used to overbook CPUs.")
    ]
    bandwidth_in: Annotated[
        float, Field(default=10, description="Input network bandwidth.")
    ]
    bandwidth_out: Annotated[
        float, Field(default=10, description="Output network bandwidth.")
    ]
    default_public_net: Annotated[
        str | None,
        Field(default=None, description="Name of the default public network"),
    ]
    default_private_net: Annotated[
        str | None,
        Field(default=None, description="Name of the default private network"),
    ]
    private_net_proxy_host: Annotated[
        str | IPvAnyAddress | None,
        Field(
            default=None,
            description="Proxy IP address or hostname with/without the port",
        ),
    ]
    private_net_proxy_user: Annotated[
        str | None,
        Field(
            default=None, description="Username to use when performing ssh operations"
        ),
    ]
    ca_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Path to the CA to use when connecting to a provider",
        ),
    ]
