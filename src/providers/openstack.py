"""Openstack client object to retrieve data from openstack instance."""

import logging
from typing import Any

import openstack.compute.v2.flavor
import openstack.connection
import openstack.image.v2.image
from fed_mgr.v1.providers.schemas import ProviderType
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.catalog import EndpointNotFound
from keystoneauth1.exceptions.connection import ConnectFailure, ConnectTimeout, SSLError
from keystoneauth1.exceptions.http import GatewayTimeout, NotFound, Unauthorized
from openstack import connect
from openstack.exceptions import ForbiddenException, HttpException
from pydantic import AnyHttpUrl

from src.models.flavors import Flavor
from src.models.images import Image
from src.models.networks import Network
from src.models.projects import Project
from src.models.quotas import BlockStorageQuota, ComputeQuota, NetworkQuota
from src.providers.core import ProviderClient


class OpenstackClient(ProviderClient):
    """Class to organize data retrieved from and Openstack instance."""

    def __init__(
        self,
        *,
        provider_name: str,
        provider_endpoint: AnyHttpUrl,
        region_name: str,
        project_id: str,
        idp_endpoint: AnyHttpUrl,
        idp_name: str,
        idp_protocol: str,
        idp_token: str,
        user_group: str,
        overbooking_cpu: float = 1,
        overbooking_ram: float = 1,
        bandwidth_in: float = 10,
        bandwidth_out: float = 10,
        image_tags: list[str] | None,
        network_tags: list[str] | None,
        default_public_net: str | None = None,
        default_private_net: str | None = None,
        private_net_proxy_host: str | None = None,
        private_net_proxy_user: str | None = None,
        auth_type: str = "v3oidcaccesstoken",
        timeout: int = 2,
        log_level: int = logging.INFO,
    ) -> None:
        """Create an openstack client to retrieve data."""
        super().__init__(
            provider_name=provider_name,
            provider_endpoint=str(provider_endpoint),
            provider_type=ProviderType.openstack,
            project_id=project_id,
            idp_endpoint=str(idp_endpoint),
            idp_name=idp_name,
            idp_token=idp_token,
            user_group=user_group,
            logger_name=f"{provider_name} - {region_name} - {project_id}",
            log_level=log_level,
            timeout=timeout,
        )
        self.region_name = region_name
        self.idp_protocol = idp_protocol
        self.image_tags = image_tags
        self.network_tags = network_tags
        self.overbooking_cpu = overbooking_cpu
        self.overbooking_ram = overbooking_ram
        self.bandwidth_in = bandwidth_in
        self.bandwidth_out = bandwidth_out
        self.default_public_net = default_public_net
        self.default_private_net = default_private_net
        self.private_net_proxy_host = private_net_proxy_host
        self.private_net_proxy_user = private_net_proxy_user
        self.auth_type = auth_type

        # Connection is only defined, not yet opened
        self.conn = self.create_connection()

        self.project = None
        self.flavors = []
        self.images = []
        self.networks = []
        self.quotas = []

    def create_connection(self) -> openstack.connection.Connection:
        """Create connection to Openstack provider.

        Returns:
            Connection: openstack connection instance.

        """
        msg = f"Creating connection using idp={self.idp_name}"
        self.logger.info(msg)
        return connect(
            auth_url=self.provider_endpoint,
            auth_type=self.auth_type,
            identity_provider=self.idp_name,
            protocol=self.idp_protocol,
            access_token=self.idp_token,
            project_id=self.project_id,
            region_name=self.region_name,
            timeout=self.timeout,
        )

    def retrieve_info(self) -> bool:
        """Connect to the provider e retrieve information.

        Returns:
            bool: True if the operation succeeded. False otherwise.

        """
        success = True
        try:
            self.project = self.get_project()
            block_storage_quotas = self.get_block_storage_quotas()
            compute_quotas, self.flavors, self.images = self.get_compute_resources()
            network_quotas, self.networks = self.get_network_resources()
            self.quotas = block_storage_quotas + compute_quotas + network_quotas
        except (
            ConnectFailure,
            ConnectTimeout,
            Unauthorized,
            ForbiddenException,
            NoMatchingPlugin,
            EndpointNotFound,
            NotFound,
            SSLError,
            GatewayTimeout,
            HttpException,
        ) as e:
            self.logger.error(e)
            self.logger.error("Connection aborted. Skipping project")
            success = False
        finally:
            self.conn.close()
            self.logger.info("Connection closed")
        return success

    def get_block_storage_quota_and_usage(
        self,
    ) -> tuple[BlockStorageQuota, BlockStorageQuota]:
        """Retrieve current project accessible block storage limits and usage.

        Returns:
            (BlockStorageQuota, BlockStorageQuota): in order they represents the
                resources limits and usage.

        """
        self.logger.info("Retrieve current project accessible block storage quotas")
        quota = self.conn.block_storage.get_quota_set(
            self.conn.current_project_id, usage=True
        )
        data = quota.to_dict()
        self.logger.debug("Block storage service quotas=%s", data)
        data_limits = {**data}
        data_usage = data_limits.pop("usage", {})
        self.logger.debug("Block storage service quota limits=%s", data_limits)
        self.logger.debug("Block storage service quota usage=%s", data_usage)
        return BlockStorageQuota(
            **data_limits, project=self.conn.current_project_id
        ), BlockStorageQuota(
            **data_usage, project=self.conn.current_project_id, usage=True
        )

    def get_compute_quota_and_usage(
        self,
    ) -> tuple[ComputeQuota, ComputeQuota]:
        """Retrieve current project accessible compute limits and usage.

        Returns:
            (ComputeQuota, ComputeQuota): in order they represents the resources
                limits and usage.

        """
        self.logger.info("Retrieve current project accessible compute quotas")
        quota = self.conn.compute.get_quota_set(
            self.conn.current_project_id, usage=True
        )
        data = quota.to_dict()
        self.logger.debug("Compute service quotas=%s", data)
        data_limits = {**data}
        data_usage = data_limits.pop("usage", {})
        self.logger.debug("Compute service quota limits=%s", data_limits)
        self.logger.debug("Compute service quota usage=%s", data_usage)
        return ComputeQuota(
            **data_limits, project=self.conn.current_project_id
        ), ComputeQuota(**data_usage, project=self.conn.current_project_id, usage=True)

    def get_network_quota_and_usage(
        self,
    ) -> tuple[NetworkQuota, NetworkQuota]:
        """Retrieve current project accessible networking limits and usage.

        Returns:
            (NetworkQuota, NetworkQuota): in order they represents the resources
                limits and usage.

        """
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
        return NetworkQuota(
            **data_limits, project=self.conn.current_project_id
        ), NetworkQuota(**data_usage, project=self.conn.current_project_id, usage=True)

    def get_flavor_extra_specs(self, extra_specs: dict[str, Any]) -> dict[str, Any]:
        """Format flavor extra specs into a dictionary.

        Args:
            extra_specs (dict of {str, Any}): flavor's extra specs dict retrieved from
                openstack.

        Returns:
            dict of {str, Any}): filtered information.

        """
        data = {}
        data["gpus"] = int(extra_specs.get("gpu_number", 0))
        data["gpu_model"] = extra_specs.get("gpu_model") if data["gpus"] > 0 else None
        data["gpu_vendor"] = extra_specs.get("gpu_vendor") if data["gpus"] > 0 else None
        data["local_storage"] = extra_specs.get(
            "aggregate_instance_extra_specs:local_storage"
        )
        data["infiniband"] = extra_specs.get("infiniband", False)
        return data

    def get_flavor_projects(
        self, flavor: openstack.compute.v2.flavor.Flavor
    ) -> list[str]:
        """Retrieve project ids having access to target flavor.

        Args:
            flavor (openstack.compute.v2.flavor.Flavor): openstack flavor.

        Returns:
            list of str: List of projects ids.

        Raises:
            ForbiddenException: raised from openstack when openstack policy does not
                allow the service user to read these details.
        """
        projects = set()
        for i in self.conn.compute.get_flavor_access(flavor):
            projects.add(i.get("tenant_id"))
        return list(projects)

    def get_flavors(self) -> list[Flavor]:
        """Map Openstack flavor instance into Flavor instance.

        Returns:
            list of Flavor: lits of flavors objects with the relevant and standardized
                details.

        """
        self.logger.info("Retrieve current project accessible flavors")
        flavors = []
        for flavor in self.conn.compute.flavors(is_disabled=False):
            self.logger.debug("Flavor received data=%r", flavor)
            data = flavor.to_dict()
            data["iaas_uuid"] = data.pop("id")
            if data.get("description") is None:
                data["description"] = ""
            data["is_shared"] = data.pop("is_public")
            if not data["is_shared"]:
                data["projects"] = self.get_flavor_projects(flavor)
            extra = data.pop("extra_specs")
            if extra:
                data = {**self.get_flavor_extra_specs(extra), **data}
            if data["is_shared"]:
                flavors.append(Flavor(**data))
            elif len(data["projects"]) > 0:
                flavors.append(Flavor(**data))
            else:
                msg = "Skipping private flavor with no projects. "
                msg += f"IaaS uuid: '{data['iaas_uuid']}'"
                self.logger.warning(msg)
            self.logger.debug("Flavor manipulated data=%s", data)
        return flavors

    def get_image_projects(self, image: openstack.image.v2.image.Image) -> list[str]:
        """Retrieve project ids having access to target image.

        Called only by shared (openstack definition) images.

        Args:
            image (openstack.image.v2.image.Image): openstack 'shared' image.

        Returns:
            list of str: list of the ids of the projects authorized to use this image.

        """
        projects = set([image.owner_id])
        members = list(self.conn.image.members(image))
        for member in members:
            if member.status == "accepted":
                projects.add(member.id)
        return list(projects)

    def get_images(self, *, tags: list[str] | None = None) -> list[Image]:
        """Map Openstack image istance into Image instance.

        Returns:
            list of Image: lits of images objects with the relevant and standardized
                details.

        """
        if tags is None:
            tags = []
        self.logger.info("Retrieve current project accessible images")
        images = []
        for image in self.conn.image.images(
            status="active", tag=None if len(tags) == 0 else tags
        ):
            self.logger.debug("Image received data=%r", image)
            data = image.to_dict()
            data["iaas_uuid"] = data.pop("id")
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
                images.append(Image(**data))
            else:
                images.append(Image(**data))
            self.logger.debug("Image manipulated data=%s", data)
        return images

    def is_default_network(
        self,
        *,
        network: Network,
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

    def get_networks(self, *, tags: list[str] | None = None) -> list[Network]:
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
            data["iaas_uuid"] = data.pop("id")
            if data.get("description") is None:
                data["description"] = ""
            # A project can find not owned networks. Discard them.
            if not data["is_shared"]:
                if self.conn.current_project_id != network.project_id:
                    self.logger.warning(
                        "Not shared and not owned network, but still usable"
                    )
                data["projects"] = [self.conn.current_project_id]
            if data.get("is_default", None) is None:
                data["is_default"] = False
            data["proxy_host"] = str(self.private_net_proxy_host)
            data["proxy_user"] = self.private_net_proxy_user
            self.logger.debug("Network manipulated data=%s", data)
            if data["is_shared"]:
                networks.append(Network(**data))
            else:
                networks.append(Network(**data))
        return networks

    def get_project(self) -> Project:
        """Map current project values into ProjectCreate instance."""
        self.logger.info("Retrieve current project data")
        project = self.conn.identity.get_project(self.conn.current_project_id)
        self.logger.debug("Project received data=%r", project)
        data = project.to_dict()
        data["iaas_uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        self.logger.debug("Project manipulated data=%s", data)
        return Project(**data)

    def get_block_storage_quotas(self) -> list[BlockStorageQuota]:
        """Retrieve project's block storage service.

        Remove last part which corresponds to the project ID.
        Retrieve current project corresponding quotas.
        Add them to the block storage service.
        """
        quotas = []

        endpoint = self.conn.block_storage.get_endpoint()
        if not endpoint:
            return quotas

        quotas = [*self.get_block_storage_quota_and_usage()]
        # if self.project_conf.per_user_limits.block_storage:
        #     quotas.append(
        #         BlockStorageQuota(
        #             **self.project_conf.per_user_limits.block_storage.dict(
        #                 exclude_none=True
        #             ),
        #             project=self.conn.current_project_id,
        #         )
        #     )

        return quotas

    def get_compute_resources(
        self,
    ) -> tuple[list[ComputeQuota], list[Flavor], list[Image]]:
        """Create region's compute service.

        Retrieve flavors, images and current project corresponding quotas.
        Add them to the compute service.
        """
        quotas = []
        flavors = []
        images = []

        endpoint = self.conn.compute.get_endpoint()
        if not endpoint:
            return quotas, flavors, images

        flavors = self.get_flavors()
        images = self.get_images(tags=self.image_tags)
        quotas = [*self.get_compute_quota_and_usage()]
        # if self.project_conf.per_user_limits.compute:
        #     quotas.append(
        #         ComputeQuota(
        #             **self.project_conf.per_user_limits.compute
        #   .dict(exclude_none=True),
        #             project=self.conn.current_project_id,
        #         )
        #     )

        return quotas, flavors, images

    def get_network_resources(self) -> tuple[list[NetworkQuota], list[Network]]:
        """Retrieve region's network service."""
        quotas = []
        networks = []

        endpoint = self.conn.network.get_endpoint()
        if not endpoint:
            return quotas, networks

        networks = self.get_networks(tags=self.network_tags)
        # If only one private network or only one public network, set it as default
        # Set default network when user specifies it in the configuration file
        tot_pub_nets = len([x for x in networks if x.is_router_external])
        tot_priv_nets = len([x for x in networks if not x.is_router_external])
        for network in networks:
            is_unique = (network.is_router_external and tot_pub_nets == 1) or (
                not network.is_router_external and tot_priv_nets == 1
            )
            network.is_default = self.is_default_network(
                network=network,
                default_private_net=self.default_private_net,
                default_public_net=self.default_public_net,
                is_unique=is_unique,
            )

        quotas = [*self.get_network_quota_and_usage()]
        # if self.project_conf.per_user_limits.network:
        #     quotas.append(
        #         NetworkQuota(
        #             **self.project_conf.per_user_limits.network
        #                   .dict(exclude_none=True),
        #             project=self.conn.current_project_id,
        #         )
        #     )

        return quotas, networks

    # def get_object_store_quota_and_usage(
    #     self,
    # ) -> tuple[ObjectStoreQuota, ObjectStoreQuota]:
    #     """Retrieve current project accessible object-store limits and usage.

    #     Returns:
    #         (ObjectStoreQuota, ObjectStoreQuota): in order they represents the
    #               resource limits and usage.

    #     """
    #     self.logger.info("Retrieve current project accessible object store quotas")
    #     resp: Response = self.conn.object_store.get(
    #         self.conn.object_store.get_endpoint()
    #     )
    #     info = self.conn.object_store.get_info()
    #     self.logger.debug("Object storage service headers=%s", resp.headers)
    #     self.logger.debug("Object storage service info=%s", info)
    #     data_limits = {}
    #     data_usage = {}
    #     data_usage["bytes"] = resp.headers.get("X-Account-Bytes-Used", 0)
    #     data_usage["containers"] = resp.headers.get("X-Account-Container-Count", 0)
    #     data_usage["objects"] = resp.headers.get("X-Account-Object-Count", 0)
    #     data_limits["bytes"] = resp.headers.get("X-Account-Meta-Quota-Bytes", -1)
    #     data_limits["containers"] = info.swift.get("container_listing_limit", 10000)
    #     data_limits["objects"] = -1
    #     self.logger.debug("Block storage service quota limits=%s", data_limits)
    #     self.logger.debug("Block storage service quota usage=%s", data_usage)
    #     return ObjectStoreQuota(
    #         **data_limits, project=self.conn.current_project_id
    #     ), ObjectStoreQuota(
    #         **data_usage, project=self.conn.current_project_id, usage=True
    #     )

    # def get_s3_quota_and_usage(
    #     self,
    # ) -> tuple[ObjectStoreQuota, ObjectStoreQuota]:
    #     self.logger.info("Retrieve current project accessible S3 quotas")
    #     # TODO: Understand where to retrieve quotas when dealing with S3 services.
    #     self.logger.debug("Fake quota")
    #     return ObjectStoreQuota(
    #         description="placeholder", project=self.conn.current_project_id
    #     ), ObjectStoreQuota(
    #         description="placeholder", project=self.conn.current_project_id,
    #           usage=True
    #     )

    # def get_object_store_quotas(self) -> list[ObjectStoreQuota]:
    #     """Retrieve project's object store service.

    #     Remove last part which corresponds to the project ID.
    #     Retrieve current project corresponding quotas.
    #     Add them to the object store service.
    #     """
    #     quotas = []
    #     try:
    #         endpoint = self.conn.object_store.get_endpoint()
    #     except EndpointNotFound as e:
    #         self.logger.warning(e)
    #         return quotas

    #     if not endpoint:
    #         return quotas

    #     quotas = [*self.get_object_store_quota_and_usage()]
    #     if self.project_conf.per_user_limits.object_store:
    #         quotas.append(
    #             ObjectStoreQuota(
    #                 **self.project_conf.per_user_limits.object_store.dict(
    #                     exclude_none=True
    #                 ),
    #                 project=self.conn.current_project_id,
    #             )
    #         )
    #     return quotas

    # def get_s3_services(self):
    #     """Retrieve project's object store services implementing S3.

    #     Retrieve the list of services from the service catalog.
    #     Filter them by type (S3), endpoint interface (public) and region.
    #     """
    #     s3_services = []
    #     for service in filter(
    #         lambda x: x.get("type") == "s3" and x.get("name") == "swift_s3",
    #         self.conn.service_catalog,
    #     ):
    #         for endpoint in filter(
    #             lambda x: x.get("interface") == "public"
    #             and x.get("region") == self.region_name,
    #             service.get("endpoints"),
    #         ):
    #             s3_service = ObjectStoreServiceCreateExtended(
    #                 endpoint=endpoint.get("url"),
    #                 name=ObjectStoreServiceName.OPENSTACK_SWIFT_S3,
    #             )
    #             s3_service.quotas = [*self.get_s3_quotas()]
    #             if self.project_conf.per_user_limits.object_store:
    #                 s3_service.quotas.append(
    #                     ObjectStoreQuota(
    #                         **self.project_conf.per_user_limits.object_store.dict(
    #                             exclude_none=True
    #                         ),
    #                         project=self.conn.current_project_id,
    #                     )
    #                 )
    #             s3_services.append(s3_service)
    #     return s3_services
