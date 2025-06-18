import copy
from concurrent.futures import ThreadPoolExecutor

from fedreg.v1.provider.enum import ProviderStatus
from pydantic import AnyHttpUrl

from src.logger import create_logger
from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Kubernetes, Openstack, Project, Region
from src.providers.conn_thread import ConnectionThread
from src.providers.openstack import OpenstackData, OpenstackProviderError


class ProviderThread:
    """Provider data shared between the same thread."""

    def __init__(
        self,
        *,
        provider_conf: Openstack | Kubernetes,
        issuers: list[Issuer],
        log_level: str | int | None = None,
    ) -> None:
        self.provider_conf = provider_conf
        self.issuers = issuers
        self.log_level = log_level
        self.logger = create_logger(
            f"Provider {self.provider_conf.name}", level=log_level
        )
        self.error = False

    def prepare_project_conf(self, *, project: Project, region_name: str) -> Project:
        """Get project parameters defined in the yaml file.

        If the `per_region_props` attribute has been defined and the current region name
        matches the name of the region definining the new props, override project's
        corresponding values.
        """
        # Find region props matching current region.
        region_props = filter(
            lambda x: x.region_name == region_name, project.per_region_props
        )
        region_props = next(region_props, None)

        item = Project(**project.dict(exclude={"per_region_props"}))
        if region_props:
            item.default_private_net = region_props.default_private_net
            item.default_public_net = region_props.default_public_net
            item.private_net_proxy = region_props.private_net_proxy
            item.per_user_limits = region_props.per_user_limits
        return item

    def retrieve_data(self, item: ConnectionThread) -> OpenstackData | None:
        """Get provider data"""
        try:
            return item.get_provider_data()
        except OpenstackProviderError:
            self.error = True
        except NotImplementedError as e:
            self.error = True
            self.logger.error(e)
        return None

    def get_issuer_matching_project(self, project_sla: str) -> Issuer:
        """Find the identity provider with an SLA matching the target project's one.

        For each sla of each user group of each issuer listed in the yaml file, find the
        one matching the SLA of the target project.

        Return the indentity provider data and the token to use to establish the
        connection.
        """
        for issuer in self.issuers:
            for user_group in issuer.user_groups:
                for sla in user_group.slas:
                    if sla.doc_uuid == project_sla:
                        return Issuer(
                            **issuer.dict(by_alias=True, exclude={"user_groups"}),
                            user_groups=[
                                {
                                    **user_group.dict(exclude={"slas"}),
                                    "slas": [{**sla.dict()}],
                                }
                            ],
                        )
        raise ValueError(f"No SLA matches project's doc_uuid `{project_sla}`")

    def get_auth_method_matching_issuer(
        self, issuer_endpoint: AnyHttpUrl
    ) -> AuthMethod:
        for auth_method in self.provider_conf.identity_providers:
            if auth_method.endpoint == issuer_endpoint:
                return auth_method
        trusted_endpoints = [i.endpoint for i in self.provider_conf.identity_providers]
        raise ValueError(
            f"No identity provider matches endpoint `{issuer_endpoint}` in "
            f"provider's trusted identity providers {trusted_endpoints}."
        )

    def get_connection_thread(
        self, *, project: Project, region: Region
    ) -> ConnectionThread | None:
        try:
            project_conf = self.prepare_project_conf(
                project=project, region_name=region.name
            )
            issuer = self.get_issuer_matching_project(project_conf.sla)
            auth_method = self.get_auth_method_matching_issuer(issuer.endpoint)
            provider_conf = copy.deepcopy(self.provider_conf)
            provider_conf.regions = [region]
            provider_conf.projects = [project_conf]
            provider_conf.identity_providers = [auth_method]
            return ConnectionThread(
                provider_conf=provider_conf,
                issuer=issuer,
                log_level=self.log_level,
            )
        except (ValueError, AssertionError) as e:
            self.error = True
            self.logger.error(e)
            self.logger.error("Skipping project")
        return None

    def get_provider(self) -> tuple[Openstack | Kubernetes, list[OpenstackData], bool]:
        """Generate a list of generic providers.

        Read data from real instances.
        For each provider returns the given configuration and the list of retrieved data
        for each established connection.
        Supported providers:
        - Openstack
        """
        if self.provider_conf.status != ProviderStatus.ACTIVE.value:
            self.logger.info("Provider not active: %s", self.provider_conf.status)
            return self.provider_conf, [], False

        # For each couple (region-project), create a separated thread and try to connect
        # to the provider
        connections: list[ConnectionThread] = []
        for region in self.provider_conf.regions:
            for project in self.provider_conf.projects:
                conn_thread = self.get_connection_thread(project=project, region=region)
                if conn_thread is not None:
                    connections.append(conn_thread)

        with ThreadPoolExecutor() as executor:
            provider_data = executor.map(self.retrieve_data, connections)
        provider_data = list(provider_data)
        provider_data = list(filter(lambda x: x is not None, provider_data))
        self.error |= any([x.error for x in connections])

        return self.provider_conf, provider_data, self.error
