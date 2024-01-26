import copy
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List, Optional, Tuple

from app.provider.enum import ProviderStatus
from app.provider.schemas_extended import (
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
    ProviderCreateExtended,
    RegionCreateExtended,
)
from app.quota.schemas import BlockStorageQuotaBase, ComputeQuotaBase, NetworkQuotaBase
from app.service.enum import (
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
from src.models.identity_provider import Issuer
from src.models.provider import PrivateNetProxy, Project
from src.providers.core import (
    filter_projects_on_compute_resources,
    get_identity_provider_info_for_project,
    get_project_conf_params,
    update_identity_providers,
    update_region_block_storage_services,
    update_region_compute_services,
    update_region_identity_services,
    update_region_network_services,
)

TIMEOUT = 2  # s

projects_lock = Lock()
region_lock = Lock()
issuer_lock = Lock()


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
        data = flavor.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        extra = data.pop("extra_specs")
        if extra:
            data["gpus"] = int(extra.get("gpu_number", 0))
            data["gpu_model"] = extra.get("gpu_model") if data["gpus"] > 0 else None
            data["gpu_vendor"] = extra.get("gpu_vendor") if data["gpus"] > 0 else None
            data["local_storage"] = extra.get(
                "aggregate_instance_extra_specs:local_storage"
            )
            data["infiniband"] = extra.get("infiniband", False)
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
        if image.visibility in ["private", "shared"]:
            projects = [image.owner_id]
            is_public = False
        if image.visibility == "shared":
            projects = get_image_projects(conn, image=image, projects=projects)
        data = image.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
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
    return (
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
            data["proxy_ip"] = str(proxy.ip)
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
    project_id: str,
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
                **per_user_limits.dict(exclude_none=True), project=project_id
            )
        )
    return block_storage_service


def get_compute_service(
    conn: Connection,
    *,
    per_user_limits: Optional[ComputeQuotaBase],
    project_id: str,
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
                **per_user_limits.dict(exclude_none=True), project=project_id
            )
        )
    return compute_service


def get_network_service(
    conn: Connection,
    *,
    per_user_limits: Optional[NetworkQuotaBase],
    project_id: str,
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
                **per_user_limits.dict(exclude_none=True), project=project_id
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
) -> Optional[Connection]:
    """Connect to Openstack provider"""
    logger.info(
        f"Connecting through IDP {idp.endpoint} to openstack "
        f"'{provider_conf.name}' and region '{region_name}'. "
        f"Accessing with project ID: {project_id}"
    )
    auth_type = "v3oidcaccesstoken"
    try:
        conn = connect(
            auth_url=provider_conf.auth_url,
            auth_type=auth_type,
            identity_provider=idp.relationship.idp_name,
            protocol=idp.relationship.protocol,
            access_token=token,
            project_id=project_id,
            region_name=region_name,
            timeout=TIMEOUT,
        )
    except (ConnectFailure, Unauthorized, NoMatchingPlugin, NotFound) as e:
        logger.error(e)
        return None
    logger.info("Connected.")
    return conn


def get_provider_resources(
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
    if not conn:
        return None

    try:
        # Create project entity
        project = get_project(conn)

        # Retrieve provider services (block_storage, compute, identity and network)
        block_storage_service = get_block_storage_service(
            conn,
            per_user_limits=project_conf.per_user_limits.block_storage,
            project_id=project_conf.id,
        )
        compute_service = get_compute_service(
            conn,
            per_user_limits=project_conf.per_user_limits.compute,
            project_id=project_conf.id,
            tags=provider_conf.image_tags,
        )
        identity_service = IdentityServiceCreate(
            endpoint=provider_conf.auth_url,
            name=IdentityServiceName.OPENSTACK_KEYSTONE,
        )
        network_service = get_network_service(
            conn,
            per_user_limits=project_conf.per_user_limits.network,
            project_id=project_conf.id,
            tags=provider_conf.network_tags,
            default_private_net=project_conf.default_private_net,
            default_public_net=project_conf.default_public_net,
            proxy=project_conf.private_net_proxy,
        )

        conn.close()
        logger.info("Connection closed")
    except ConnectFailure:
        logger.error("Connection closed unexpectedly.")
        return None

    return (
        project,
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    )


def get_project_resources(
    *,
    provider_conf: Openstack,
    project_conf: Project,
    issuers: List[Issuer],
    out_region: RegionCreateExtended,
    out_projects: List[ProjectCreate],
    out_issuers: List[IdentityProviderCreateExtended],
) -> None:
    # Find region props matching current region.
    region_props = next(
        filter(
            lambda x: x.region_name == out_region.name,
            project_conf.per_region_props,
        ),
        None,
    )
    proj_conf = get_project_conf_params(
        project_conf=project_conf, region_props=region_props
    )

    try:
        identity_provider, token = get_identity_provider_info_for_project(
            issuers=issuers,
            trusted_issuers=provider_conf.identity_providers,
            project=proj_conf,
        )
    except ValueError as e:
        logger.error(e)
        logger.error(f"Skipping project {proj_conf.id}.")
        return None

    resp = get_provider_resources(
        provider_conf=provider_conf,
        project_conf=proj_conf,
        identity_provider=identity_provider,
        token=token,
        region_name=out_region.name,
    )
    if not resp:
        return None

    (
        project,
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    ) = resp
    with region_lock:
        update_region_block_storage_services(
            current_services=out_region.block_storage_services,
            new_service=block_storage_service,
        )
        update_region_compute_services(
            current_services=out_region.compute_services, new_service=compute_service
        )
        update_region_identity_services(
            current_services=out_region.identity_services, new_service=identity_service
        )
        update_region_network_services(
            current_services=out_region.network_services, new_service=network_service
        )

    with projects_lock:
        if project.uuid not in [i.uuid for i in out_projects]:
            out_projects.append(project)

    with issuer_lock:
        update_identity_providers(
            current_issuers=out_issuers, new_issuer=identity_provider
        )


def get_provider(
    *, os_conf: Openstack, trusted_idps: List[Issuer]
) -> ProviderCreateExtended:
    """Generate an Openstack virtual provider, reading information from a real openstack
    instance.
    """
    if os_conf.status != ProviderStatus.ACTIVE.value:
        logger.info(f"Provider={os_conf.name} not active: {os_conf.status}")
        return ProviderCreateExtended(
            name=os_conf.name,
            type=os_conf.type,
            is_public=os_conf.is_public,
            support_emails=os_conf.support_emails,
            status=os_conf.status,
        )

    trust_idps = copy.deepcopy(trusted_idps)
    regions: List[RegionCreateExtended] = []
    projects: List[ProjectCreate] = []
    identity_providers: List[IdentityProviderCreateExtended] = []

    for region_conf in os_conf.regions:
        region = RegionCreateExtended(**region_conf.dict())
        thread_pool = ThreadPoolExecutor(max_workers=len(os_conf.projects))
        for project_conf in os_conf.projects:
            thread_pool.submit(
                get_project_resources,
                provider_conf=os_conf,
                project_conf=project_conf,
                issuers=trust_idps,
                out_region=region,
                out_projects=projects,
                out_issuers=identity_providers,
            )
        thread_pool.shutdown(wait=True)
        regions.append(region)

    for region in regions:
        filter_projects_on_compute_resources(
            region=region, include_projects=[i.uuid for i in projects]
        )

    return ProviderCreateExtended(
        name=os_conf.name,
        type=os_conf.type,
        is_public=os_conf.is_public,
        support_emails=os_conf.support_emails,
        status=os_conf.status,
        identity_providers=identity_providers,
        projects=projects,
        regions=regions,
    )
