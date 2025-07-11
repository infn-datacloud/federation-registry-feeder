import os
from logging import Logger
from typing import Any

from fedreg.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    BlockStorageServiceCreateExtended,
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkQuotaCreateExtended,
    NetworkServiceCreateExtended,
    ObjectStoreQuotaCreateExtended,
    ObjectStoreServiceCreateExtended,
    PrivateFlavorCreateExtended,
    PrivateImageCreateExtended,
    PrivateNetworkCreateExtended,
    ProjectCreate,
    SharedFlavorCreate,
    SharedImageCreate,
    SharedNetworkCreate,
)
from fedreg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
    ObjectStoreServiceName,
)
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.catalog import EndpointNotFound
from keystoneauth1.exceptions.connection import ConnectFailure, ConnectTimeout, SSLError
from keystoneauth1.exceptions.http import GatewayTimeout, NotFound, Unauthorized
from openstack import connect
from openstack.compute.v2.flavor import Flavor
from openstack.connection import Connection
from openstack.exceptions import ForbiddenException, HttpException
from openstack.image.v2.image import Image
from requests import Response

from src.models.identity_provider import Issuer
from src.models.provider import PrivateNetProxy
from src.models.site_config import Openstack

TIMEOUT = 2  # s


class OpenstackProviderError(Exception):
    """Raised when data retrieval from an openstack provider fails."""


class OpenstackData:
    """Class to organize data retrieved from and Openstack instance."""

    def __init__(
        self, *, provider_conf: Openstack, issuer: Issuer, logger: Logger
    ) -> None:
        self.error = False
        self.logger = logger
        try:
            assert len(provider_conf.regions) == 1, (
                f"Invalid number or regions: {len(provider_conf.regions)}"
            )
            assert len(provider_conf.projects) == 1, (
                f"Invalid number or projects: {len(provider_conf.projects)}"
            )
            msg = "Invalid number or trusted identity providers: "
            msg += f"{len(provider_conf.identity_providers)}"
            assert len(provider_conf.identity_providers) == 1, msg

            self.provider_conf = provider_conf
            self.project_conf = provider_conf.projects[0]
            self.auth_method = provider_conf.identity_providers[0]
            self.region_name = provider_conf.regions[0].name
            self.issuer = issuer

            self.project = None
            self.block_storage_services = []
            self.compute_services = []
            self.identity_services = []
            self.network_services = []
            self.object_store_services = []

            # Connection is only defined, not yet opened
            self.conn = self.create_connection(token=self.issuer.token)

            # Retrieve information
            self.retrieve_info()
        except AssertionError as e:
            self.error = True
            self.logger.error(e)
            raise OpenstackProviderError from e

    def retrieve_info(self) -> None:
        """Connect to the provider e retrieve information"""
        try:
            self.identity_services = [
                IdentityServiceCreate(
                    endpoint=self.provider_conf.auth_url,
                    name=IdentityServiceName.OPENSTACK_KEYSTONE,
                )
            ]

            # Create project entity
            self.project = self.get_project()

            # Retrieve provider services (block_storage, compute, identity and network)
            srv = self.get_block_storage_service()
            if srv is not None:
                self.block_storage_services.append(srv)
            srv = self.get_compute_service()
            if srv is not None:
                self.compute_services.append(srv)
            srv = self.get_network_service()
            if srv is not None:
                self.network_services.append(srv)
            self.object_store_services = []
            # object_store_service = self.get_object_store_service()
            # if object_store_service is not None:
            #     self.object_store_services.append(object_store_service)
            self.object_store_services += self.get_s3_services()
        except (
            ConnectFailure,
            ConnectTimeout,
            Unauthorized,
            NoMatchingPlugin,
            NotFound,
            ForbiddenException,
            SSLError,
            GatewayTimeout,
            HttpException,
        ) as e:
            self.error = True
            self.logger.error(e)
            self.logger.error("Connection aborted. Skipping project")
            raise OpenstackProviderError from e
        self.conn.close()
        self.logger.info("Connection closed")

    def to_dict(self) -> dict:
        return {
            "provider_conf": self.provider_conf.dict(),
            "issuer": self.issuer.dict(),
            "project": self.project.dict(),
            "block_storage_services": [i.dict() for i in self.block_storage_services],
            "compute_services": [i.dict() for i in self.compute_services],
            "identity_services": [i.dict() for i in self.identity_services],
            "network_services": [i.dict() for i in self.network_services],
            "object_store_services": [i.dict() for i in self.object_store_services],
        }

    def create_connection(self, *, token: str) -> Connection:
        """Connect to Openstack provider"""
        self.logger.info(
            "Connecting through IDP '%s' to openstack '%s' and region '%s'",
            self.auth_method.endpoint,
            self.provider_conf.name,
            self.region_name,
        )
        self.logger.info("Accessing with project ID: %s", self.project_conf.id)
        auth_type = "v3oidcaccesstoken"
        return connect(
            auth_url=self.provider_conf.auth_url,
            auth_type=auth_type,
            identity_provider=self.auth_method.idp_name,
            protocol=self.auth_method.protocol,
            access_token=token,
            project_id=self.project_conf.id,
            region_name=self.region_name,
            timeout=TIMEOUT,
        )

    def get_block_storage_quotas(
        self,
    ) -> tuple[BlockStorageQuotaCreateExtended, BlockStorageQuotaCreateExtended]:
        """Retrieve current project accessible block storage quota"""
        self.logger.info("Retrieve current project accessible block storage quotas")
        try:
            quota = self.conn.block_storage.get_quota_set(
                self.conn.current_project_id, usage=True
            )
            data = quota.to_dict()
        except ForbiddenException as e:
            self.logger.error(e)
            self.error = True
            data = {}
        self.logger.debug("Block storage service quotas=%s", data)
        data_limits = {**data}
        data_usage = data_limits.pop("usage", {})
        self.logger.debug("Block storage service quota limits=%s", data_limits)
        self.logger.debug("Block storage service quota usage=%s", data_usage)
        return BlockStorageQuotaCreateExtended(
            **data_limits, project=self.conn.current_project_id
        ), BlockStorageQuotaCreateExtended(
            **data_usage, project=self.conn.current_project_id, usage=True
        )

    def get_compute_quotas(
        self,
    ) -> tuple[ComputeQuotaCreateExtended, ComputeQuotaCreateExtended]:
        """Retrieve current project accessible compute quota"""
        self.logger.info("Retrieve current project accessible compute quotas")
        quota = self.conn.compute.get_quota_set(
            self.conn.current_project_id,
            base_path="/os-quota-sets/%(project_id)s/detail",
        )
        data = quota.to_dict()
        self.logger.debug("Compute service quotas=%s", data)
        data_limits = {**data}
        data_usage = data_limits.pop("usage", {})
        self.logger.debug("Compute service quota limits=%s", data_limits)
        self.logger.debug("Compute service quota usage=%s", data_usage)
        return ComputeQuotaCreateExtended(
            **data_limits, project=self.conn.current_project_id
        ), ComputeQuotaCreateExtended(
            **data_usage, project=self.conn.current_project_id, usage=True
        )

    def get_network_quotas(
        self,
    ) -> tuple[NetworkQuotaCreateExtended, NetworkQuotaCreateExtended]:
        """Retrieve current project accessible network quota"""
        self.logger.info("Retrieve current project accessible network quotas")
        quota = self.conn.network.get_quota(self.conn.current_project_id, details=True)
        data = quota.to_dict()
        self.logger.debug("Network service quotas=%s", data)
        data_limits = {}
        data_usage = {}
        for k, v in data.items():
            new_k = "public_ips" if k == "floating_ips" else k
            if v is not None:
                data_limits[new_k] = v.get("limit")
                data_usage[new_k] = v.get("used")
        self.logger.debug("Network service quota limits=%s", data_limits)
        self.logger.debug("Network service quota usage=%s", data_usage)
        return NetworkQuotaCreateExtended(
            **data_limits, project=self.conn.current_project_id
        ), NetworkQuotaCreateExtended(
            **data_usage, project=self.conn.current_project_id, usage=True
        )

    def get_object_store_quotas(
        self,
    ) -> tuple[ObjectStoreQuotaCreateExtended, ObjectStoreQuotaCreateExtended]:
        self.logger.info("Retrieve current project accessible object store quotas")
        resp: Response = self.conn.object_store.get(
            self.conn.object_store.get_endpoint()
        )
        info = self.conn.object_store.get_info()
        self.logger.debug("Object storage service headers=%s", resp.headers)
        self.logger.debug("Object storage service info=%s", info)
        data_limits = {}
        data_usage = {}
        data_usage["bytes"] = resp.headers.get("X-Account-Bytes-Used", 0)
        data_usage["containers"] = resp.headers.get("X-Account-Container-Count", 0)
        data_usage["objects"] = resp.headers.get("X-Account-Object-Count", 0)
        data_limits["bytes"] = resp.headers.get("X-Account-Meta-Quota-Bytes", -1)
        data_limits["containers"] = info.swift.get("container_listing_limit", 10000)
        data_limits["objects"] = -1
        self.logger.debug("Block storage service quota limits=%s", data_limits)
        self.logger.debug("Block storage service quota usage=%s", data_usage)
        return ObjectStoreQuotaCreateExtended(
            **data_limits, project=self.conn.current_project_id
        ), ObjectStoreQuotaCreateExtended(
            **data_usage, project=self.conn.current_project_id, usage=True
        )

    def get_s3_quotas(
        self,
    ) -> tuple[ObjectStoreQuotaCreateExtended, ObjectStoreQuotaCreateExtended]:
        self.logger.info("Retrieve current project accessible S3 quotas")
        # TODO: Understand where to retrieve quotas when dealing with S3 services.
        self.logger.debug("Fake quota")
        return ObjectStoreQuotaCreateExtended(
            description="placeholder", project=self.conn.current_project_id
        ), ObjectStoreQuotaCreateExtended(
            description="placeholder", project=self.conn.current_project_id, usage=True
        )

    def get_flavor_extra_specs(self, extra_specs: dict[str, Any]) -> dict[str, Any]:
        """Format flavor extra specs into a dictionary."""
        data = {}
        data["gpus"] = int(extra_specs.get("gpu_number", 0))
        data["gpu_model"] = extra_specs.get("gpu_model") if data["gpus"] > 0 else None
        data["gpu_vendor"] = extra_specs.get("gpu_vendor") if data["gpus"] > 0 else None
        data["local_storage"] = extra_specs.get(
            "aggregate_instance_extra_specs:local_storage"
        )
        data["infiniband"] = extra_specs.get("infiniband", False)
        return data

    def get_flavor_projects(self, flavor: Flavor) -> list[str]:
        """Retrieve project ids having access to target flavor."""
        projects = set()
        try:
            for i in self.conn.compute.get_flavor_access(flavor):
                projects.add(i.get("tenant_id"))
        except ForbiddenException as e:
            self.logger.error(e)
            self.error = True
        return list(projects)

    def get_flavors(self) -> list[PrivateFlavorCreateExtended | SharedFlavorCreate]:
        """Map Openstack flavor instance into FlavorCreateExtended instance."""
        self.logger.info("Retrieve current project accessible flavors")
        flavors = []
        for flavor in self.conn.compute.flavors(is_disabled=False):
            self.logger.debug("Flavor received data=%r", flavor)
            data = flavor.to_dict()
            data["uuid"] = data.pop("id")
            if data.get("description") is None:
                data["description"] = ""
            data["is_shared"] = data.pop("is_public")
            if not data["is_shared"]:
                data["projects"] = self.get_flavor_projects(flavor)
            extra = data.pop("extra_specs")
            if extra:
                data = {**self.get_flavor_extra_specs(extra), **data}
            if data["is_shared"]:
                flavors.append(SharedFlavorCreate(**data))
            elif len(data["projects"]) > 0:
                flavors.append(PrivateFlavorCreateExtended(**data))
            self.logger.debug("Flavor manipulated data=%s", data)
        return flavors

    def get_image_projects(self, image: Image) -> list[str]:
        """Retrieve project ids having access to target image.

        Called only by shared images.
        """
        projects = set([image.owner_id])
        members = list(self.conn.image.members(image))
        for member in members:
            if member.status == "accepted":
                projects.add(member.id)
        return list(projects)

    def get_images(
        self, *, tags: list[str] | None = None
    ) -> list[PrivateImageCreateExtended | SharedImageCreate]:
        """Map Openstack image istance into ImageCreateExtended instance."""
        if tags is None:
            tags = []
        self.logger.info("Retrieve current project accessible images")
        images = []
        for image in self.conn.image.images(
            status="active", tag=None if len(tags) == 0 else tags
        ):
            self.logger.debug("Image received data=%r", image)
            data = image.to_dict()
            data["uuid"] = data.pop("id")
            # Openstack image object does not have `description` field
            data["description"] = ""
            # At least one project is present since the image is visible from the
            # current project.
            if image.visibility == "private":
                data["is_shared"] = False
                data["projects"] = [image.owner_id]
            elif image.visibility == "shared":
                data["is_shared"] = False
                data["projects"] = self.get_image_projects(image)
            else:
                data["is_shared"] = True
            if data["is_shared"]:
                images.append(SharedImageCreate(**data))
            else:
                images.append(PrivateImageCreateExtended(**data))
            self.logger.debug("Image manipulated data=%s", data)
        return images

    def is_default_network(
        self,
        *,
        network: PrivateNetworkCreateExtended | SharedNetworkCreate,
        default_private_net: str | None = None,
        default_public_net: str | None = None,
        is_unique: bool = False,
    ) -> bool:
        """Detect if this network is the default one."""
        return bool(
            (is_unique and network.is_router_external and default_public_net is None)
            or (
                is_unique
                and not network.is_router_external
                and default_private_net is None
            )
            or (network.is_router_external and default_public_net == network.name)
            or (not network.is_router_external and default_private_net == network.name)
            or network.is_default
        )

    def get_networks(
        self, *, proxy: PrivateNetProxy | None = None, tags: list[str] | None = None
    ) -> list[PrivateNetworkCreateExtended | SharedNetworkCreate]:
        """Map Openstack network instance in NetworkCreateExtended instance."""
        if tags is None:
            tags = []
        self.logger.info("Retrieve current project accessible networks")
        networks = []
        for network in self.conn.network.networks(
            status="active", tag=None if len(tags) == 0 else tags
        ):
            self.logger.debug("Network received data=%r", network)
            data = network.to_dict()
            data["uuid"] = data.pop("id")
            if data.get("description") is None:
                data["description"] = ""
            # A project can find not owned networks. Discard them.
            if not data["is_shared"]:
                if self.conn.current_project_id != network.project_id:
                    self.logger.warning(
                        "Not shared and not owned network, but still usable"
                    )
                data["projects"] = [self.conn.current_project_id]
            if proxy:
                data["proxy_host"] = str(proxy.host)
                data["proxy_user"] = proxy.user
            self.logger.debug("Network manipulated data=%s", data)
            if data["is_shared"]:
                networks.append(SharedNetworkCreate(**data))
            else:
                networks.append(PrivateNetworkCreateExtended(**data))
        return networks

    def get_project(self) -> ProjectCreate:
        """Map current project values into ProjectCreate instance."""
        self.logger.info("Retrieve current project data")
        project = self.conn.identity.get_project(self.conn.current_project_id)
        self.logger.debug("Project received data=%r", project)
        data = project.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        self.logger.debug("Project manipulated data=%s", data)
        return ProjectCreate(**data)

    def get_block_storage_service(self) -> BlockStorageServiceCreateExtended | None:
        """Retrieve project's block storage service.

        Remove last part which corresponds to the project ID.
        Retrieve current project corresponding quotas.
        Add them to the block storage service.
        """
        try:
            endpoint = self.conn.block_storage.get_endpoint()
        except EndpointNotFound as e:
            self.logger.error(e)
            self.error = True
            return None
        if not endpoint:
            return None

        block_storage_service = BlockStorageServiceCreateExtended(
            endpoint=os.path.dirname(endpoint),
            name=BlockStorageServiceName.OPENSTACK_CINDER,
        )
        block_storage_service.quotas = [*self.get_block_storage_quotas()]
        if self.project_conf.per_user_limits.block_storage:
            block_storage_service.quotas.append(
                BlockStorageQuotaCreateExtended(
                    **self.project_conf.per_user_limits.block_storage.dict(
                        exclude_none=True
                    ),
                    project=self.conn.current_project_id,
                )
            )
        return block_storage_service

    def get_compute_service(self) -> ComputeServiceCreateExtended | None:
        """Create region's compute service.

        Retrieve flavors, images and current project corresponding quotas.
        Add them to the compute service.
        """
        try:
            endpoint = self.conn.compute.get_endpoint()
        except EndpointNotFound as e:
            self.logger.error(e)
            self.error = True
            return None
        if not endpoint:
            return None

        compute_service = ComputeServiceCreateExtended(
            endpoint=endpoint, name=ComputeServiceName.OPENSTACK_NOVA
        )
        compute_service.flavors = self.get_flavors()
        compute_service.images = self.get_images(tags=self.provider_conf.image_tags)
        compute_service.quotas = [*self.get_compute_quotas()]
        if self.project_conf.per_user_limits.compute:
            compute_service.quotas.append(
                ComputeQuotaCreateExtended(
                    **self.project_conf.per_user_limits.compute.dict(exclude_none=True),
                    project=self.conn.current_project_id,
                )
            )
        return compute_service

    def get_network_service(self) -> NetworkServiceCreateExtended | None:
        """Retrieve region's network service."""
        try:
            endpoint = self.conn.network.get_endpoint()
        except EndpointNotFound as e:
            self.logger.error(e)
            self.error = True
            return None
        if not endpoint:
            return None

        network_service = NetworkServiceCreateExtended(
            endpoint=endpoint, name=NetworkServiceName.OPENSTACK_NEUTRON
        )
        network_service.networks = self.get_networks(
            proxy=self.project_conf.private_net_proxy,
            tags=self.provider_conf.network_tags,
        )
        # If only one private network or only one public network, set it as default
        # Set default network when user specifies it in the configuration file
        tot_pub_nets = len(
            [x for x in network_service.networks if x.is_router_external]
        )
        tot_priv_nets = len(
            [x for x in network_service.networks if not x.is_router_external]
        )
        for network in network_service.networks:
            is_unique = (network.is_router_external and tot_pub_nets == 1) or (
                not network.is_router_external and tot_priv_nets == 1
            )
            network.is_default = self.is_default_network(
                network=network,
                default_private_net=self.project_conf.default_private_net,
                default_public_net=self.project_conf.default_public_net,
                is_unique=is_unique,
            )
        network_service.quotas = [*self.get_network_quotas()]
        if self.project_conf.per_user_limits.network:
            network_service.quotas.append(
                NetworkQuotaCreateExtended(
                    **self.project_conf.per_user_limits.network.dict(exclude_none=True),
                    project=self.conn.current_project_id,
                )
            )
        return network_service

    def get_object_store_service(self) -> ObjectStoreServiceCreateExtended | None:
        """Retrieve project's object store service.

        Remove last part which corresponds to the project ID.
        Retrieve current project corresponding quotas.
        Add them to the object store service.
        """
        try:
            endpoint = self.conn.object_store.get_endpoint()
        except EndpointNotFound as e:
            self.logger.warning(e)
            return None
        if not endpoint:
            return None

        object_store_service = ObjectStoreServiceCreateExtended(
            endpoint=os.path.dirname(endpoint),
            name=ObjectStoreServiceName.OPENSTACK_SWIFT,
        )
        object_store_service.quotas = [*self.get_object_store_quotas()]
        if self.project_conf.per_user_limits.object_store:
            object_store_service.quotas.append(
                ObjectStoreQuotaCreateExtended(
                    **self.project_conf.per_user_limits.object_store.dict(
                        exclude_none=True
                    ),
                    project=self.conn.current_project_id,
                )
            )
        return object_store_service

    def get_s3_services(self):
        """Retrieve project's object store services implementing S3.

        Retrieve the list of services from the service catalog.
        Filter them by type (S3), endpoint interface (public) and region.
        """
        s3_services = []
        for service in filter(
            lambda x: x.get("type") == "s3" and x.get("name") == "swift_s3",
            self.conn.service_catalog,
        ):
            for endpoint in filter(
                lambda x: x.get("interface") == "public"
                and x.get("region") == self.region_name,
                service.get("endpoints"),
            ):
                s3_service = ObjectStoreServiceCreateExtended(
                    endpoint=endpoint.get("url"),
                    name=ObjectStoreServiceName.OPENSTACK_SWIFT_S3,
                )
                s3_service.quotas = [*self.get_s3_quotas()]
                if self.project_conf.per_user_limits.object_store:
                    s3_service.quotas.append(
                        ObjectStoreQuotaCreateExtended(
                            **self.project_conf.per_user_limits.object_store.dict(
                                exclude_none=True
                            ),
                            project=self.conn.current_project_id,
                        )
                    )
                s3_services.append(s3_service)
        return s3_services
