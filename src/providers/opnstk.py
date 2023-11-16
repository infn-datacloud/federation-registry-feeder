import copy
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List, Optional

from app.provider.enum import ProviderStatus
from app.provider.schemas_extended import (
    BlockStorageQuotaCreateExtended,
    BlockStorageServiceCreateExtended,
    ComputeQuotaCreateExtended,
    ComputeServiceCreateExtended,
    FlavorCreateExtended,
    IdentityServiceCreate,
    ImageCreateExtended,
    NetworkCreateExtended,
    NetworkQuotaCreateExtended,
    NetworkServiceCreateExtended,
    ProjectCreate,
    ProviderCreateExtended,
    RegionCreateExtended,
    SLACreateExtended,
    UserGroupCreateExtended,
)
from app.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
)
from logger import logger
from models.provider import (
    AuthMethod,
    Openstack,
    PrivateNetProxy,
    Project,
    TrustedIDP,
)
from openstack import connect
from openstack.connection import Connection

TIMEOUT = 2  # s

projects_lock = Lock()
region_lock = Lock()


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


def get_flavors(conn: Connection) -> List[FlavorCreateExtended]:
    logger.info("Retrieve current project accessible flavors")
    flavors = []
    for flavor in conn.compute.flavors(is_disabled=False):
        logger.debug(f"Flavor received data={flavor!r}")
        projects = []
        if not flavor.is_public:
            for i in conn.compute.get_flavor_access(flavor):
                projects.append(i.get("tenant_id"))
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
        flavors.append(FlavorCreateExtended(**data, projects=projects))
    return flavors


def get_images(
    conn: Connection, tags: Optional[List[str]] = None
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
            members = list(conn.image.members(image))
            for member in members:
                if member.status == "accepted":
                    projects.append(member.id)
        data = image.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        data["is_public"] = is_public
        logger.debug(f"Image manipulated data={data}")
        images.append(ImageCreateExtended(**data, projects=projects))
    return images


def get_networks(
    conn: Connection,
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
            project = conn.current_project_id
        data = network.to_dict()
        data["uuid"] = data.pop("id")
        if data.get("description") is None:
            data["description"] = ""
        if data.get("is_default") is None:
            if (network.is_shared and default_public_net == network.name) or (
                not network.is_shared and default_private_net == network.name
            ):
                data["is_default"] = True
            else:
                data["is_default"] = False
        if proxy is not None:
            data["proxy_ip"] = proxy.ip
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


def get_correct_idp_and_user_group_for_project(
    *,
    trusted_idps: List[TrustedIDP],
    os_conf_auth_methods: List[AuthMethod],
    project_conf: Project,
) -> TrustedIDP:
    for trusted_idp in trusted_idps:
        for user_group in trusted_idp.user_groups:
            for sla in user_group.slas:
                if sla.doc_uuid == project_conf.sla:
                    if project_conf.id not in sla.projects:
                        sla.projects.append(project_conf.id)
                        for auth_method in os_conf_auth_methods:
                            if auth_method.endpoint == trusted_idp.endpoint:
                                trusted_idp.relationship = auth_method
                                return trusted_idp
                    return trusted_idp

    logger.error(
        "Configuration error: No matching Identity Provider "
        f"for project {project_conf.id}"
    )
    raise


def get_per_project_details(
    os_conf: Openstack,
    project_conf: Project,
    region: RegionCreateExtended,
    trusted_idps: List[TrustedIDP],
    projects: List[ProjectCreate],
) -> None:
    default_private_net = project_conf.default_private_net
    default_public_net = project_conf.default_public_net
    proxy = project_conf.private_net_proxy
    per_user_limits = project_conf.per_user_limits
    region_props = next(
        filter(
            lambda x: x.region_name == region.name,
            project_conf.per_region_props,
        ),
        None,
    )

    if region_props is not None:
        default_private_net = region_props.default_private_net
        default_public_net = region_props.default_public_net
        proxy = region_props.private_net_proxy
        per_user_limits = region_props.per_user_limits

    trusted_idp = get_correct_idp_and_user_group_for_project(
        os_conf_auth_methods=os_conf.identity_providers,
        trusted_idps=trusted_idps,
        project_conf=project_conf,
    )
    if trusted_idp is None:
        logger.error(f"Skipping project {project_conf.id}.")
        return

    logger.info(
        f"Connecting through IDP {trusted_idp.endpoint} to openstack "
        f"'{os_conf.name}' and region '{region.name}'. "
        f"Accessing with project ID: {project_conf.id}"
    )
    conn = connect(
        auth_url=os_conf.auth_url,
        auth_type="v3oidcaccesstoken",
        identity_provider=trusted_idp.relationship.idp_name,
        protocol=trusted_idp.relationship.protocol,
        access_token=trusted_idp.token,
        project_id=project_conf.id,
        region_name=region.name,
        timeout=TIMEOUT,
    )
    logger.info("Connected.")

    # Create region's compute service.
    # Retrieve flavors, images and current project corresponding quotas.
    # Add them to the compute service.
    compute_service = ComputeServiceCreateExtended(
        endpoint=conn.compute.get_endpoint(), name=ComputeServiceName.OPENSTACK_NOVA
    )
    compute_service.flavors = get_flavors(conn)
    compute_service.images = get_images(conn, tags=os_conf.image_tags)
    compute_service.quotas = [get_compute_quotas(conn)]
    if per_user_limits is not None and per_user_limits.compute is not None:
        compute_service.quotas.append(
            ComputeQuotaCreateExtended(
                **per_user_limits.compute.dict(exclude_none=True),
                project=project_conf.id,
            )
        )

    with region_lock:
        for i, region_service in enumerate(region.compute_services):
            if region_service.endpoint == compute_service.endpoint:
                uuids = [j.uuid for j in region_service.flavors]
                region.compute_services[i].flavors += list(
                    filter(lambda x: x.uuid not in uuids, compute_service.flavors)
                )
                uuids = [j.uuid for j in region_service.images]
                region.compute_services[i].images += list(
                    filter(lambda x: x.uuid not in uuids, compute_service.images)
                )
                region.compute_services[i].quotas += compute_service.quotas
                break
        else:
            region.compute_services.append(compute_service)

    # Retrieve project's block storage service.
    # Remove last part which corresponds to the project ID.
    # Retrieve current project corresponding quotas.
    # Add them to the block storage service.
    endpoint = conn.block_storage.get_endpoint()
    endpoint = os.path.dirname(endpoint)
    block_storage_service = BlockStorageServiceCreateExtended(
        endpoint=endpoint, name=BlockStorageServiceName.OPENSTACK_CINDER
    )
    block_storage_service.quotas = [get_block_storage_quotas(conn)]
    if per_user_limits is not None and per_user_limits.block_storage is not None:
        block_storage_service.quotas.append(
            BlockStorageQuotaCreateExtended(
                **per_user_limits.block_storage.dict(exclude_none=True),
                project=project_conf.id,
            )
        )

    with region_lock:
        for i, region_service in enumerate(region.block_storage_services):
            if region_service.endpoint == block_storage_service.endpoint:
                region.block_storage_services[i].quotas += block_storage_service.quotas
                break
        else:
            region.block_storage_services.append(block_storage_service)

    # Retrieve region's network service.
    network_service = NetworkServiceCreateExtended(
        endpoint=conn.network.get_endpoint(),
        name=NetworkServiceName.OPENSTACK_NEUTRON,
    )
    network_service.networks = get_networks(
        conn,
        default_private_net=default_private_net,
        default_public_net=default_public_net,
        proxy=proxy,
        tags=os_conf.network_tags,
    )
    network_service.quotas = [get_network_quotas(conn)]
    if per_user_limits is not None and per_user_limits.network is not None:
        network_service.quotas.append(
            NetworkQuotaCreateExtended(
                **per_user_limits.compute.dict(exclude_none=True),
                project=project_conf.id,
            )
        )

    with region_lock:
        for i, region_service in enumerate(region.network_services):
            if region_service.endpoint == network_service.endpoint:
                uuids = [j.uuid for j in region_service.networks]
                region.network_services[i].networks += list(
                    filter(lambda x: x.uuid not in uuids, network_service.networks)
                )
                break
        else:
            region.network_services.append(network_service)

    # Retrieve provider's identity service.
    identity_service = IdentityServiceCreate(
        endpoint=os_conf.auth_url,
        name=IdentityServiceName.OPENSTACK_KEYSTONE,
    )
    with region_lock:
        for region_service in region.identity_services:
            if region_service.endpoint == identity_service.endpoint:
                break
        else:
            region.identity_services.append(identity_service)

    # Create project entity
    project = get_project(conn)
    with projects_lock:
        if project.uuid not in [i.uuid for i in projects]:
            projects.append(project)

    conn.close()
    logger.info("Connection closed")


def get_provider(
    *, os_conf: Openstack, trusted_idps: List[TrustedIDP]
) -> ProviderCreateExtended:
    """Generate an Openstack virtual provider, reading information from a real openstack
    instance.
    """
    if os_conf.status != ProviderStatus.ACTIVE:
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

    for region_conf in os_conf.regions:
        region = RegionCreateExtended(**region_conf.dict())
        thread_pool = ThreadPoolExecutor(max_workers=len(os_conf.projects))
        for project_conf in os_conf.projects:
            thread_pool.submit(
                get_per_project_details,
                os_conf=os_conf,
                project_conf=project_conf,
                region=region,
                trusted_idps=trust_idps,
                projects=projects,
            )
        thread_pool.shutdown(wait=True)
        regions.append(region)

    # Filter on IDPs and user groups with SLAs
    # belonging to at least one project
    for idp in trust_idps:
        user_groups = []
        for user_group in idp.user_groups:
            for sla in user_group.slas:
                if len(sla.projects) == 1:
                    project = sla.projects[0]
                    new_sla = SLACreateExtended(**sla.dict(), project=project)
                    new_group = UserGroupCreateExtended(
                        **user_group.dict(), sla=new_sla
                    )
                    user_groups.append(new_group)
        idp.user_groups = user_groups
    identity_providers = list(filter(lambda idp: len(idp.user_groups) > 0, trust_idps))

    # Remove from flavors and images' projects the ones
    # that have not been imported in the Federation Registry
    projects_uuid = [i.uuid for i in projects]
    for region in regions:
        for service in region.compute_services:
            for flavor in service.flavors:
                flavor.projects = list(
                    filter(lambda x: x in projects_uuid, flavor.projects)
                )
            for image in service.images:
                image.projects = list(
                    filter(lambda x: x in projects_uuid, image.projects)
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
