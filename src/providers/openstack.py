import os
from typing import Any, Dict, List, Optional, Tuple

from fed_reg.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    BlockStorageServiceCreateExtended,
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    ImageCreateExtended,
    NetworkCreateExtended,
    NetworkQuotaCreateExtended,
    NetworkServiceCreateExtended,
    ProjectCreate,
)
from fed_reg.quota.schemas import (
    BlockStorageQuotaBase,
    ComputeQuotaBase,
    NetworkQuotaBase,
)
from fed_reg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
)
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.catalog import EndpointNotFound
from keystoneauth1.exceptions.connection import ConnectFailure
from keystoneauth1.exceptions.http import NotFound, Unauthorized
from openstack import connect
from openstack.compute.v2.flavor import Flavor
from openstack.connection import Connection
from openstack.image.v2.image import Image
from openstack.network.v2.network import Network

from src.logger import logger
from src.models.config import Openstack
from src.models.provider import PrivateNetProxy, Project

TIMEOUT = 2  # s


def get_block_storage_quotas(conn: Connection) -> BlockStorageQuotaCreateExtended:
    logger.info("Retrieve current project accessible block storage quotas")
    quota = conn.block_storage.get_quota_set(conn.current_project_id)
    data = quota.to_dict()
    logger.debug(f"Block storage service quotas={data}")
    return BlockStorageQuotaCreateExtended(**data, project=conn.current_project_id)


def get_compute_quotas(conn: Connection) -> ComputeQuotaCreateExtended:
    logger.info("Retrieve current project accessible compute quotas")
    quota = conn.compute.get_quota_set(conn.current_project_id)
    data = quota.to_dict()
    logger.debug(f"Compute service quotas={data}")
    return ComputeQuotaCreateExtended(**data, project=conn.current_project_id)


def get_network_quotas(conn: Connection) -> NetworkQuotaCreateExtended:
    logger.info("Retrieve current project accessible network quotas")
    quota = conn.network.get_quota(conn.current_project_id)
    data = quota.to_dict()
    data["public_ips"] = data.pop("floating_ips")
    logger.debug(f"Network service quotas={data}")
    return NetworkQuotaCreateExtended(**data, project=conn.current_project_id)


def get_flavor_extra_specs(extra_specs: Dict[str, Any]) -> Dict[str, Any]:
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


def get_flavor_projects(conn: Connection, flavor: Flavor) -> List[str]:
    """Retrieve project ids having access to target flavor."""
    projects = set()
    for i in conn.compute.get_flavor_access(flavor):
        projects.add(i.get("tenant_id"))
    return list(projects)


def get_flavors(conn: Connection) -> List[FlavorCreateExtended]:
    logger.info("Retrieve current project accessible flavors")
    flavors = []
    for flavor in conn.compute.flavors(is_disabled=False):
        logger.debug(f"Flavor received data={flavor!r}")
        projects = []
        if not flavor.is_public:
            projects = get_flavor_projects(conn, flavor)
            if conn.current_project_id not in projects:
                continue
        data = flavor.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        extra = data.pop("extra_specs")
        if extra:
            data = {**get_flavor_extra_specs(extra), **data}
        logger.debug(f"Flavor manipulated data={data}")
        flavors.append(FlavorCreateExtended(**data, projects=list(projects)))
    return flavors


def get_image_projects(
    conn: Connection, *, image: Image, projects: List[str]
) -> List[str]:
    """Retrieve project ids having access to target image."""
    projects = set(projects)
    members = list(conn.image.members(image))
    for member in members:
        if member.status == "accepted":
            projects.add(member.id)
    return list(projects)


def get_images(
    conn: Connection, *, tags: Optional[List[str]] = None
) -> List[ImageCreateExtended]:
    if tags is None:
        tags = []
    logger.info("Retrieve current project accessible images")
    images = []
    for image in conn.image.images(
        status="active", tag=None if len(tags) == 0 else tags
    ):
        logger.debug(f"Image received data={image!r}")
        is_public = True
        projects = []
        if image.visibility == "private":
            if conn.current_project_id != image.owner_id:
                continue
            projects = [image.owner_id]
            is_public = False
        elif image.visibility == "shared":
            projects = get_image_projects(conn, image=image, projects=projects)
            if conn.current_project_id not in projects:
                continue
            is_public = False
        data = image.to_dict()
        data["uuid"] = data.pop("id")
        # Openstack image object does not have `description` field
        data["description"] = ""
        data["is_public"] = is_public
        logger.debug(f"Image manipulated data={data}")
        images.append(ImageCreateExtended(**data, projects=list(projects)))
    return images


def is_default_network(
    *,
    network: Network,
    default_private_net: Optional[str] = None,
    default_public_net: Optional[str] = None,
) -> bool:
    """Detect if this network is the default one."""
    return bool(
        (network.is_shared and default_public_net == network.name)
        or (not network.is_shared and default_private_net == network.name)
        or network.is_default
    )


def get_networks(
    conn: Connection,
    *,
    default_private_net: Optional[str] = None,
    default_public_net: Optional[str] = None,
    proxy: Optional[PrivateNetProxy] = None,
    tags: Optional[List[str]] = None,
) -> List[NetworkCreateExtended]:
    if tags is None:
        tags = []
    logger.info("Retrieve current project accessible networks")
    networks = []
    for network in conn.network.networks(
        status="active", tag=None if len(tags) == 0 else tags
    ):
        logger.debug(f"Network received data={network!r}")
        project = None
        if not network.is_shared:
            if conn.current_project_id != network.project_id:
                continue
            else:
                project = network.project_id
        data = network.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        data["is_default"] = is_default_network(
            network=network,
            default_private_net=default_private_net,
            default_public_net=default_public_net,
        )
        if proxy:
            data["proxy_host"] = str(proxy.host)
            data["proxy_user"] = proxy.user
        logger.debug(f"Network manipulated data={data}")
        networks.append(NetworkCreateExtended(**data, project=project))
    return networks


def get_project(conn: Connection) -> ProjectCreate:
    logger.info("Retrieve current project data")
    project = conn.identity.get_project(conn.current_project_id)
    logger.debug(f"Project received data={project!r}")
    data = project.to_dict()
    data["uuid"] = data.pop("id")
    if data.get("description") is None:
        data["description"] = ""
    logger.debug(f"Project manipulated data={data}")
    return ProjectCreate(**data)


def get_block_storage_service(
    conn: Connection,
    *,
    per_user_limits: Optional[BlockStorageQuotaBase],
) -> Optional[BlockStorageServiceCreateExtended]:
    """Retrieve project's block storage service.

    Remove last part which corresponds to the project ID.
    Retrieve current project corresponding quotas.
    Add them to the block storage service.
    """
    try:
        endpoint = conn.block_storage.get_endpoint()
    except EndpointNotFound as e:
        logger.error(e)
        return None
    if not endpoint:
        return None

    block_storage_service = BlockStorageServiceCreateExtended(
        endpoint=os.path.dirname(endpoint),
        name=BlockStorageServiceName.OPENSTACK_CINDER,
    )
    block_storage_service.quotas = [get_block_storage_quotas(conn)]
    if per_user_limits:
        block_storage_service.quotas.append(
            BlockStorageQuotaCreateExtended(
                **per_user_limits.dict(exclude_none=True),
                project=conn.current_project_id,
            )
        )
    return block_storage_service


def get_compute_service(
    conn: Connection,
    *,
    per_user_limits: Optional[ComputeQuotaBase],
    tags: List[str],
) -> Optional[ComputeServiceCreateExtended]:
    """Create region's compute service.

    Retrieve flavors, images and current project corresponding quotas.
    Add them to the compute service.
    """
    try:
        endpoint = conn.compute.get_endpoint()
    except EndpointNotFound as e:
        logger.error(e)
        return None
    if not endpoint:
        return None

    compute_service = ComputeServiceCreateExtended(
        endpoint=endpoint, name=ComputeServiceName.OPENSTACK_NOVA
    )
    compute_service.flavors = get_flavors(conn)
    compute_service.images = get_images(conn, tags=tags)
    compute_service.quotas = [get_compute_quotas(conn)]
    if per_user_limits:
        compute_service.quotas.append(
            ComputeQuotaCreateExtended(
                **per_user_limits.dict(exclude_none=True),
                project=conn.current_project_id,
            )
        )
    return compute_service


def get_network_service(
    conn: Connection,
    *,
    per_user_limits: Optional[NetworkQuotaBase],
    tags: List[str],
    default_private_net: Optional[str],
    default_public_net: Optional[str],
    proxy: Optional[PrivateNetProxy],
) -> Optional[NetworkServiceCreateExtended]:
    """Retrieve region's network service."""
    try:
        endpoint = conn.network.get_endpoint()
    except EndpointNotFound as e:
        logger.error(e)
        return None
    if not endpoint:
        return None

    network_service = NetworkServiceCreateExtended(
        endpoint=endpoint, name=NetworkServiceName.OPENSTACK_NEUTRON
    )
    network_service.networks = get_networks(
        conn,
        default_private_net=default_private_net,
        default_public_net=default_public_net,
        proxy=proxy,
        tags=tags,
    )
    network_service.quotas = [get_network_quotas(conn)]
    if per_user_limits:
        network_service.quotas.append(
            NetworkQuotaCreateExtended(
                **per_user_limits.dict(exclude_none=True),
                project=conn.current_project_id,
            )
        )
    return network_service


def connect_to_provider(
    *,
    provider_conf: Openstack,
    idp: IdentityProviderCreateExtended,
    project_id: str,
    region_name: str,
    token: str,
) -> Connection:
    """Connect to Openstack provider"""
    logger.info(
        f"Connecting through IDP {idp.endpoint} to openstack "
        f"'{provider_conf.name}' and region '{region_name}'. "
        f"Accessing with project ID: {project_id}"
    )
    auth_type = "v3oidcaccesstoken"
    return connect(
        auth_url=provider_conf.auth_url,
        auth_type=auth_type,
        identity_provider=idp.relationship.idp_name,
        protocol=idp.relationship.protocol,
        access_token=token,
        project_id=project_id,
        region_name=region_name,
        timeout=TIMEOUT,
    )


def get_data_from_openstack(
    *,
    provider_conf: Openstack,
    project_conf: Project,
    identity_provider: IdentityProviderCreateExtended,
    region_name: str,
    token: str,
) -> Optional[
    Tuple[
        ProjectCreate,
        Optional[BlockStorageServiceCreateExtended],
        Optional[ComputeServiceCreateExtended],
        IdentityServiceCreate,
        Optional[NetworkServiceCreateExtended],
    ]
]:
    conn = connect_to_provider(
        provider_conf=provider_conf,
        idp=identity_provider,
        project_id=project_conf.id,
        region_name=region_name,
        token=token,
    )

    try:
        # Create project entity
        project = get_project(conn)

        # Retrieve provider services (block_storage, compute, identity and network)
        block_storage_service = get_block_storage_service(
            conn, per_user_limits=project_conf.per_user_limits.block_storage
        )
        compute_service = get_compute_service(
            conn,
            per_user_limits=project_conf.per_user_limits.compute,
            tags=provider_conf.image_tags,
        )
        identity_service = IdentityServiceCreate(
            endpoint=provider_conf.auth_url,
            name=IdentityServiceName.OPENSTACK_KEYSTONE,
        )
        network_service = get_network_service(
            conn,
            per_user_limits=project_conf.per_user_limits.network,
            tags=provider_conf.network_tags,
            default_private_net=project_conf.default_private_net,
            default_public_net=project_conf.default_public_net,
            proxy=project_conf.private_net_proxy,
        )
    except (ConnectFailure, Unauthorized, NoMatchingPlugin, NotFound) as e:
        logger.error(e)
        return None

    # TODO Check if the closing action can raise an exception
    conn.close()
    logger.info("Connection closed")

    return (
        project,
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    )
