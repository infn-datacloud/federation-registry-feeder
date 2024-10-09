import os
from random import getrandbits, randint
from typing import Any
from uuid import uuid4

import pytest
from fed_reg.provider.schemas_extended import (
    AuthMethodCreate,
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ProjectCreate,
    RegionCreateExtended,
    SLACreateExtended,
    UserGroupCreateExtended,
)
from openstack.block_storage.v3.quota_set import (
    QuotaSet as OpenstackBlockStorageQuotaSet,
)
from openstack.compute.v2.flavor import Flavor as OpenstackFlavor
from openstack.compute.v2.quota_set import QuotaSet as OpenstackComputeQuotaSet
from openstack.image.v2.image import Image as OpenstackImage
from openstack.network.v2.network import Network as OpenstackNetwork
from openstack.network.v2.quota import QuotaDetails as OpenstackNetworkQuota
from pytest_cases import case, parametrize, parametrize_with_cases

from tests.providers.openstack.utils import random_image_status, random_network_status
from tests.schemas.utils import (
    random_block_storage_service_name,
    random_compute_service_name,
    random_float,
    random_identity_service_name,
    random_image_os_type,
    random_lower_string,
    random_network_service_name,
    random_url,
    sla_dict,
)


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    """Clear the OS environment."""
    os.environ.clear()


# @pytest.fixture
# def crud() -> CRUD:
#     """Fixture with a CRUD object.

#     The CRUD object is used to interact with the federation-registry API.
#     """
#     read_header, write_header = get_read_write_headers(token=random_lower_string())
#     return CRUD(
#         url=random_url(),
#         read_headers=read_header,
#         write_headers=write_header,
#         logger=logging.getLogger(),
#     )


# @pytest.fixture
# def api_ver() -> APIVersions:
#     """Fixture with an APIVersions object.

#     The APIVersions object is used to store the API versions to use when interacting
#     with the federation-registry API.
#     """
#     return APIVersions()


# @pytest.fixture
# def settings(api_ver: APIVersions) -> Settings:
#     """Fixture with a Settings object.

#     The Settings object stores the project settings.
#     """
#     return Settings(api_ver=api_ver)


# @pytest.fixture
# def service_endpoints() -> URLs:
#     """Fixture with a URLs object.

#     The URLs object stores the federation-registry service endpoints.
#     """
#     base_url = random_url()
#     return URLs(**{k: os.path.join(base_url, k) for k in URLs.__fields__.keys()})


# # Identity Providers configurations


# @pytest.fixture
# def sla() -> SLA:
#     """Fixture with an SLA without projects."""
#     start_date, end_date = random_start_end_dates()
#     return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


# @pytest.fixture
# def user_group(sla: SLA) -> UserGroup:
#     """Fixture with a UserGroup with one SLA."""
#     return UserGroup(name=random_lower_string(), slas=[sla])


# @pytest.fixture
# def issuer(user_group: UserGroup) -> Issuer:
#     """Fixture with an Issuer with one UserGroup."""
#     return Issuer(
#         issuer=random_url(),
#         group_claim=random_lower_string(),
#         token=random_lower_string(),
#         user_groups=[user_group],
#     )


# # Providers configurations


# @pytest.fixture
# def auth_method() -> AuthMethod:
#     """Fixture with an AuthMethod."""
#     return AuthMethod(
#         name=random_lower_string(),
#         protocol=random_lower_string(),
#         endpoint=random_url(),
#     )


# @pytest.fixture
# def limits() -> Limits:
#     """Fixture with an empty Limits object."""
#     return Limits()


# @pytest.fixture
# def net_proxy() -> PrivateNetProxy:
#     """Fixture with an PrivateNetProxy."""
#     return PrivateNetProxy(host=random_ip(), user=random_lower_string())


# @pytest.fixture
# def per_region_props() -> PerRegionProps:
#     """Fixture with a minimal PerRegionProps object."""
#     return PerRegionProps(region_name=random_lower_string())


# @pytest.fixture
# def project() -> Project:
#     """Fixture with a Project with an SLA."""
#     return Project(id=uuid4(), sla=uuid4())


# @pytest.fixture
# def region() -> Region:
#     """Fixture with a Region."""
#     return Region(name=random_lower_string())


# @pytest.fixture
# def openstack_provider(auth_method: AuthMethod, project: Project) -> Openstack:
#     """Fixture with an Openstack provider.

#     It has an authentication method and a project.
#     """
#     return Openstack(
#         name=random_lower_string(),
#         auth_url=random_url(),
#         identity_providers=[auth_method],
#         projects=[project],
#     )


# @pytest.fixture
# def kubernetes_provider(auth_method: AuthMethod, project: Project) -> Kubernetes:
#     """Fixture with a Kubernetes provider.

#     It has an authentication method and a project.
#     """
#     return Kubernetes(
#         name=random_lower_string(),
#         auth_url=random_url(),
#         identity_providers=[auth_method],
#         projects=[project],
#     )


# @pytest.fixture
# def site_config(issuer: Issuer) -> SiteConfig:
#     """Fixture with a SiteConfig with an Issuer and no providers."""
#     return SiteConfig(trusted_idps=[issuer])


# @pytest.fixture
# def configurations(
#     identity_provider_create: IdentityProviderCreateExtended,
#     openstack_provider: Openstack,
#     project: Project,
# ) -> tuple[IdentityProviderCreateExtended, Openstack, Project]:
#     project.sla = identity_provider_create.user_groups[0].sla.doc_uuid
#     openstack_provider.identity_providers[
#         0
#     ].endpoint = identity_provider_create.endpoint
#     openstack_provider.identity_providers[
#         0
#     ].idp_name = identity_provider_create.relationship.idp_name
#     openstack_provider.identity_providers[
#         0
#     ].protocol = identity_provider_create.relationship.protocol
#     return identity_provider_create, openstack_provider, project


# # Federation-Registry Base Items


# @pytest.fixture
# def location() -> LocationBase:
#     """Fixture with an LocationBase without projects."""
#     return LocationBase(site=random_lower_string(), country=random_country())


# @pytest.fixture
# def block_storage_quota() -> BlockStorageQuotaBase:
#     """Fixture with a BlockStorageQuotaBase."""
#     return BlockStorageQuotaBase(
#         gigabytes=randint(0, 100),
#         per_volume_gigabytes=randint(0, 100),
#         volumes=randint(1, 100),
#     )


# @pytest.fixture
# def compute_quota() -> ComputeQuotaBase:
#     """Fixture with a ComputeQuotaBase."""
#     return ComputeQuotaBase(
#         cores=randint(0, 100),
#         instances=randint(0, 100),
#         ram=randint(1, 100),
#     )


# @pytest.fixture
# def network_quota() -> NetworkQuotaBase:
#     """Fixture with a NetworkQuotaBase."""
#     return NetworkQuotaBase(
#         public_ips=randint(0, 100),
#         networks=randint(0, 100),
#         ports=randint(1, 100),
#         security_groups=randint(1, 100),
#         security_group_rules=randint(1, 100),
#     )


# Federation-Registry Creation Items


# @pytest.fixture
# def provider_create() -> ProviderCreateExtended:
#     """Fixture with a ProviderCreateExtended."""
#     return ProviderCreateExtended(
#         name=random_lower_string(), type=random_provider_type()
#     )


# @pytest.fixture
# def provider_read(provider_create: ProviderCreateExtended) -> ProviderRead:
#     return ProviderRead(uid=uuid4(), **provider_create.dict())


# @pytest.fixture
# def provider_read_extended(
#     provider_create: ProviderCreateExtended,
# ) -> ProviderReadExtended:
#     return ProviderReadExtended(uid=uuid4(), **provider_create.dict())


@pytest.fixture
def project_create() -> ProjectCreate:
    """Fixture with a ProjectCreate."""
    return ProjectCreate(uuid=uuid4(), name=random_lower_string())


@pytest.fixture
def block_storage_service_create() -> BlockStorageServiceCreateExtended:
    """Fixture with a BlockStorageServiceCreateExtended."""
    return BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=random_block_storage_service_name()
    )


@pytest.fixture
def compute_service_create() -> ComputeServiceCreateExtended:
    """Fixture with a ComputeServiceCreateExtended."""
    return ComputeServiceCreateExtended(
        endpoint=random_url(), name=random_compute_service_name()
    )


@pytest.fixture
def identity_service_create() -> IdentityServiceCreate:
    """Fixture with an IdentityServiceCreate."""
    return IdentityServiceCreate(
        endpoint=random_url(), name=random_identity_service_name()
    )


@pytest.fixture
def network_service_create() -> NetworkServiceCreateExtended:
    """Fixture with a NetworkServiceCreateExtended."""
    return NetworkServiceCreateExtended(
        endpoint=random_url(), name=random_network_service_name()
    )


@pytest.fixture
@parametrize(
    s=[
        block_storage_service_create,
        compute_service_create,
        identity_service_create,
        network_service_create,
    ]
)
def service_create(
    s: BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | IdentityServiceCreate
    | NetworkServiceCreateExtended,
) -> (
    BlockStorageServiceCreateExtended
    | ComputeServiceCreateExtended
    | IdentityServiceCreate
    | NetworkServiceCreateExtended
):
    """Parametrized fixture with all possible services.

    BlockStorageServiceCreateExtended, ComputeServiceCreateExtended,
    IdentityServiceCreate and NetworkServiceCreateExtended.
    """
    return s


@pytest.fixture
def sla_create() -> SLACreateExtended:
    """Fixture with an SLACreateExtended."""
    return SLACreateExtended(**sla_dict(), project=uuid4())


@pytest.fixture
def user_group_create(sla_create: SLACreateExtended) -> UserGroupCreateExtended:
    """Fixture with a UserGroupCreateExtended."""
    return UserGroupCreateExtended(name=random_lower_string(), sla=sla_create)


@pytest.fixture
def auth_method_create() -> AuthMethodCreate:
    return AuthMethodCreate(
        idp_name=random_lower_string(), protocol=random_lower_string()
    )


@pytest.fixture
def identity_provider_create(
    auth_method_create: AuthMethodCreate, user_group_create: UserGroupCreateExtended
) -> IdentityProviderCreateExtended:
    """Fixture with an IdentityProviderCreateExtended."""
    return IdentityProviderCreateExtended(
        user_groups=[user_group_create],
        endpoint=random_url(),
        group_claim=random_lower_string(),
        relationship=auth_method_create,
    )


@pytest.fixture
def region_create(
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    identity_service_create: IdentityServiceCreate,
    network_service_create: NetworkServiceCreateExtended,
):
    """Fixture with a RegionCreateExtended"""
    return RegionCreateExtended(
        name=random_lower_string(),
        block_storage_services=[block_storage_service_create],
        compute_services=[compute_service_create],
        identity_services=[identity_service_create],
        network_services=[network_service_create],
    )


# Openstack specific


class CaseDefaultAttr:
    @parametrize(value=[True, False])
    def case_is_default(self, value: bool) -> bool:
        return value


class CaseTags:
    def case_single_valid_tag(self) -> list[str]:
        return ["one"]

    @parametrize(case=[0, 1])
    def case_single_invalid_tag(self, case: int) -> list[str]:
        return ["two"] if case else ["one-two"]

    def case_at_least_one_valid_tag(self) -> list[str]:
        return ["one", "two"]


def openstack_network_dict() -> dict[str, Any]:
    """dict with network minimal data."""
    return {
        "id": uuid4().hex,
        "name": random_lower_string(),
        "status": "active",
        "project_id": uuid4().hex,
        "is_router_external": getrandbits(1),
        "is_shared": False,
        "mtu": randint(1, 100),
    }


@pytest.fixture
def openstack_network_base() -> OpenstackNetwork:
    """Fixture with network."""
    return OpenstackNetwork(**openstack_network_dict())


@pytest.fixture
def openstack_network_disabled() -> OpenstackNetwork:
    """Fixture with disabled network."""
    d = openstack_network_dict()
    d["status"] = random_network_status(exclude=["active"])
    return OpenstackNetwork(**d)


@pytest.fixture
def openstack_network_with_desc() -> OpenstackNetwork:
    """Fixture with network with specified description."""
    d = openstack_network_dict()
    d["description"] = random_lower_string()
    return OpenstackNetwork(**d)


@pytest.fixture
def openstack_network_shared() -> OpenstackNetwork:
    """Fixture with shared network."""
    d = openstack_network_dict()
    d["is_shared"] = True
    return OpenstackNetwork(**d)


@pytest.fixture
@parametrize_with_cases("tags", cases=CaseTags)
def openstack_network_with_tags(tags: list[str]) -> OpenstackNetwork:
    """Fixture with network with specified tags."""
    d = openstack_network_dict()
    d["tags"] = tags
    return OpenstackNetwork(**d)


@pytest.fixture
@parametrize(i=[openstack_network_base, openstack_network_shared])
def openstack_priv_pub_network(i: OpenstackNetwork) -> OpenstackNetwork:
    """Fixtures union."""
    return i


@pytest.fixture
@parametrize(
    i=[
        openstack_priv_pub_network,
        openstack_network_disabled,
        openstack_network_with_desc,
        openstack_network_with_tags,
    ]
)
def openstack_network(i: OpenstackNetwork) -> OpenstackNetwork:
    """Fixtures union."""
    return i


@pytest.fixture
@parametrize(n=[openstack_network_base, openstack_network_shared])
@parametrize_with_cases("is_default", cases=CaseDefaultAttr)
def openstack_default_network(
    n: OpenstackNetwork, is_default: bool
) -> OpenstackNetwork:
    """Shared and not shared networks with/without is_default."""
    n.is_default = is_default
    return n


class CaseVisibility:
    @case(tags=["private"])
    @parametrize(visibility=["shared", "private"])
    def case_priv_visibility(self, visibility: str) -> str:
        return visibility

    @case(tags=["public"])
    @parametrize(visibility=["public", "community"])
    def case_pub_visibility(self, visibility: str) -> str:
        return visibility


def openstack_image_dict() -> dict[str, Any]:
    """dict with image minimal data."""
    return {
        "id": uuid4().hex,
        "name": random_lower_string(),
        "status": "active",
        "owner_id": uuid4().hex,
        "os_type": random_image_os_type(),
        "os_distro": random_lower_string(),
        "os_version": random_lower_string(),
        "architecture": random_lower_string(),
        "kernel_id": random_lower_string(),
        "visibility": "public",
    }


@pytest.fixture
def openstack_image_disabled() -> OpenstackImage:
    """Fixture with disabled image."""
    d = openstack_image_dict()
    d["status"] = random_image_status(exclude=["active"])
    return OpenstackImage(**d)


@pytest.fixture
@parametrize_with_cases("visibility", cases=CaseVisibility, has_tag="public")
def openstack_image_public(visibility: str) -> OpenstackImage:
    """Fixture with image with specified visibility."""
    d = openstack_image_dict()
    d["visibility"] = visibility
    return OpenstackImage(**d)


@pytest.fixture
@parametrize_with_cases("tags", cases=CaseTags)
def openstack_image_with_tags(tags: list[str]) -> OpenstackImage:
    """Fixture with image with specified tags."""
    d = openstack_image_dict()
    d["tags"] = tags
    return OpenstackImage(**d)


@pytest.fixture
@parametrize_with_cases("visibility", cases=CaseVisibility, has_tag="private")
def openstack_image_private(visibility: str) -> OpenstackImage:
    """Fixture with private image."""
    d = openstack_image_dict()
    d["visibility"] = visibility
    return OpenstackImage(**d)


@pytest.fixture
@parametrize(
    i=[openstack_image_disabled, openstack_image_public, openstack_image_with_tags]
)
def openstack_image(i: OpenstackImage) -> OpenstackImage:
    """Fixtures union."""
    return i


class CaseExtraSpecs:
    @parametrize(second_attr=["gpu_model", "gpu_vendor"])
    def case_gpu(self, second_attr: str) -> dict[str, Any]:
        return {"gpu_number": randint(1, 100), second_attr: random_lower_string()}

    def case_infiniband(self) -> dict[str, Any]:
        return {"infiniband": getrandbits(1)}

    def case_local_storage(self) -> dict[str, Any]:
        return {"aggregate_instance_extra_specs:local_storage": random_lower_string()}


def openstack_flavor_dict() -> dict[str, Any]:
    """dict with flavor minimal data."""
    return {
        "name": random_lower_string(),
        "disk": randint(0, 100),
        "is_public": getrandbits(1),
        "ram": randint(0, 100),
        "vcpus": randint(0, 100),
        "swap": randint(0, 100),
        "ephemeral": randint(0, 100),
        "is_disabled": False,
        "rxtx_factor": random_float(0, 100),
        "extra_specs": {},
    }


@pytest.fixture
def openstack_flavor_base() -> OpenstackFlavor:
    """Fixture with disabled flavor."""
    return OpenstackFlavor(**openstack_flavor_dict())


@pytest.fixture
def openstack_flavor_disabled() -> OpenstackFlavor:
    """Fixture with disabled flavor."""
    d = openstack_flavor_dict()
    d["is_disabled"] = True
    return OpenstackFlavor(**d)


@pytest.fixture
def openstack_flavor_with_desc() -> OpenstackFlavor:
    """Fixture with a flavor with description."""
    d = openstack_flavor_dict()
    d["description"] = random_lower_string()
    return OpenstackFlavor(**d)


@pytest.fixture
def openstack_flavor_private() -> OpenstackFlavor:
    """Fixture with private flavor."""
    d = openstack_flavor_dict()
    d["is_public"] = False
    return OpenstackFlavor(**d)


@pytest.fixture
@parametrize_with_cases("extra_specs", cases=CaseExtraSpecs)
def openstack_flavor_with_extra_specs(extra_specs: dict[str, Any]) -> OpenstackFlavor:
    """Fixture with a flavor with extra specs."""
    d = openstack_flavor_dict()
    d["extra_specs"] = extra_specs
    return OpenstackFlavor(**d)


@pytest.fixture
@parametrize(
    f=[
        openstack_flavor_base,
        openstack_flavor_disabled,
        openstack_flavor_with_extra_specs,
        openstack_flavor_private,
        openstack_flavor_with_desc,
    ]
)
def openstack_flavor(f: OpenstackFlavor) -> OpenstackFlavor:
    """Fixtures union."""
    return f


def openstack_block_storage_quotas_dict() -> dict[str, int]:
    """dict with the block storage quotas attributes."""
    return {
        "backup_gigabytes": randint(0, 100),
        "backups": randint(0, 100),
        "gigabytes": randint(0, 100),
        "groups": randint(0, 100),
        "per_volume_gigabytes": randint(0, 100),
        "snapshots": randint(0, 100),
        "volumes": randint(0, 100),
    }


def openstack_compute_quotas_dict() -> dict[str, int]:
    """dict with the compute quotas attributes."""
    return {
        "cores": randint(0, 100),
        "fixed_ips": randint(0, 100),
        "floating_ips": randint(0, 100),
        "injected_file_content_bytes": randint(0, 100),
        "injected_file_path_bytes": randint(0, 100),
        "injected_files": randint(0, 100),
        "instances": randint(0, 100),
        "key_pairs": randint(0, 100),
        "metadata_items": randint(0, 100),
        "networks": randint(0, 100),
        "ram": randint(0, 100),
        "security_group_rules": randint(0, 100),
        "security_groups": randint(0, 100),
        "server_groups": randint(0, 100),
        "server_group_members": randint(0, 100),
        "force": False,
    }


def openstack_network_quotas_dict() -> dict[str, int]:
    """dict with the network quotas attributes."""
    return {
        # "check_limit": False,
        "floating_ips": randint(0, 100),
        "health_monitors": randint(0, 100),
        "listeners": randint(0, 100),
        "load_balancers": randint(0, 100),
        "l7_policies": randint(0, 100),
        "networks": randint(0, 100),
        "pools": randint(0, 100),
        "ports": randint(0, 100),
        # "project_id": ?,
        "rbac_policies": randint(0, 100),
        "routers": randint(0, 100),
        "subnets": randint(0, 100),
        "subnet_pools": randint(0, 100),
        "security_group_rules": randint(0, 100),
        "security_groups": randint(0, 100),
    }


@pytest.fixture
def openstack_block_storage_quotas() -> OpenstackBlockStorageQuotaSet:
    """Fixture with the block storage quotas."""
    return OpenstackBlockStorageQuotaSet(
        **openstack_block_storage_quotas_dict(),
        usage=openstack_block_storage_quotas_dict(),
    )


@pytest.fixture
def openstack_compute_quotas() -> OpenstackComputeQuotaSet:
    """Fixture with the compute quotas."""
    return OpenstackComputeQuotaSet(
        **openstack_compute_quotas_dict(), usage=openstack_compute_quotas_dict()
    )


@pytest.fixture
def openstack_network_quotas() -> OpenstackNetworkQuota:
    """Fixture with the network quotas."""
    d = {}
    limit_dict = openstack_network_quotas_dict()
    usage_dict = openstack_network_quotas_dict()
    for k in limit_dict.keys():
        d[k] = {"limit": limit_dict[k], "used": usage_dict[k]}
    return OpenstackNetworkQuota(**d)
