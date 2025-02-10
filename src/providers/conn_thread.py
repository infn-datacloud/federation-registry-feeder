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

        assert len(provider_conf.regions) == 1, (
            f"Invalid number of regions: {len(provider_conf.regions)}"
        )
        assert len(provider_conf.projects) == 1, (
            f"Invalid number of projects: {len(provider_conf.projects)}"
        )
        msg = "Invalid number of trusted identity providers: "
        msg += f"{len(provider_conf.identity_providers)}"
        assert len(provider_conf.identity_providers) == 1, msg
        msg = f"Issuer endpoint {issuer.endpoint} does not match trusted identity "
        msg += f"provider's one {provider_conf.identity_providers[0].endpoint}"
        assert issuer.endpoint == provider_conf.identity_providers[0].endpoint, msg
        assert len(issuer.user_groups) == 1, (
            f"Invalid number of user groups: {len(issuer.user_groups)}"
        )
        assert len(issuer.user_groups[0].slas) == 1, (
            f"Invalid number of slas: {len(issuer.user_groups[0].slas)}"
        )

        self.provider_conf = provider_conf
        self.issuer = issuer

        logger_name = f"Provider {provider_conf.name}, "
        logger_name += f"Region {provider_conf.regions[0].name}, "
        logger_name += f"Project {provider_conf.projects[0].id}"
        self.logger = create_logger(logger_name, level=log_level)

    def get_provider_data(self) -> OpenstackData:
        """Retrieve the provider region, project and identity provider.

        From the current configuration, connect to the correct provider and retrieve the
        current configuration and resources.

        Return an object with 3 main entities: region, project and identity provider.
        """
        if isinstance(self.provider_conf, Openstack):
            return OpenstackData(
                provider_conf=self.provider_conf, issuer=self.issuer, logger=self.logger
            )
        raise NotImplementedError("Not yet implemented")
