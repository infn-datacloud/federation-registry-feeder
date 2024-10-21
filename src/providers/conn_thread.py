from fed_reg.provider.schemas_extended import (
    IdentityProviderCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
)

from src.logger import create_logger
from src.models.identity_provider import Issuer
from src.models.provider import Kubernetes, Openstack
from src.providers.openstack import OpenstackData


class ConnectionThread:
    """Data shared between the same connection socket"""

    def __init__(
        self,
        *,
        provider_conf: Openstack | Kubernetes,
        issuer: Issuer,
        log_level: str | int | None = None,
    ) -> None:
        self.error = False

        assert (
            len(provider_conf.regions) == 1
        ), f"Invalid number of regions: {len(provider_conf.regions)}"
        assert (
            len(provider_conf.projects) == 1
        ), f"Invalid number of projects: {len(provider_conf.projects)}"
        msg = "Invalid number of trusted identity providers: "
        msg += f"{len(provider_conf.identity_providers)}"
        assert len(provider_conf.identity_providers) == 1, msg
        msg = f"Issuer endpoint {issuer.endpoint} does not match trusted identity "
        msg += f"provider's one {provider_conf.identity_providers[0].endpoint}"
        assert issuer.endpoint == provider_conf.identity_providers[0].endpoint, msg
        assert (
            len(issuer.user_groups) == 1
        ), f"Invalid number of user groups: {len(issuer.user_groups)}"
        assert (
            len(issuer.user_groups[0].slas) == 1
        ), f"Invalid number of slas: {len(issuer.user_groups[0].slas)}"

        self.provider_conf = provider_conf
        self.issuer = issuer

        logger_name = f"Provider {provider_conf.name}, "
        logger_name += f"Region {provider_conf.regions[0].name}, "
        logger_name += f"Project {provider_conf.projects[0].id}"
        self.logger = create_logger(logger_name, level=log_level)

    def get_provider_components(
        self,
    ) -> tuple[IdentityProviderCreateExtended, ProjectCreate, RegionCreateExtended]:
        """Retrieve the provider region, project and identity provider.

        From the current configuration, connect to the correct provider and retrieve the
        current configuration and resources.

        Return an object with 3 main entities: region, project and identity provider.
        """
        if isinstance(self.provider_conf, Openstack):
            data = OpenstackData(
                provider_conf=self.provider_conf,
                token=self.issuer.token,
                logger=self.logger,
            )
        elif isinstance(self.provider_conf, Kubernetes):
            raise NotImplementedError("Not yet implemented")

        region = RegionCreateExtended(
            **self.provider_conf.regions[0].dict(),
            block_storage_services=data.block_storage_services,
            compute_services=data.compute_services,
            identity_services=data.identity_services,
            network_services=data.network_services,
            object_store_services=data.object_store_services,
        )
        identity_provider = IdentityProviderCreateExtended(
            description=self.issuer.description,
            group_claim=self.issuer.group_claim,
            endpoint=self.issuer.endpoint,
            relationship=self.provider_conf.identity_providers[0],
            user_groups=[
                {
                    **self.issuer.user_groups[0].dict(exclude={"slas"}),
                    "sla": {
                        **self.issuer.user_groups[0].slas[0].dict(),
                        "project": self.provider_conf.projects[0].id,
                    },
                }
            ],
        )
        return identity_provider, data.project, region
