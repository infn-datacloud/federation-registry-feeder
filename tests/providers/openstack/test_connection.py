from fed_reg.provider.schemas_extended import IdentityProviderCreateExtended

from src.models.provider import Openstack, Project
from src.providers.openstack import connect_to_provider
from tests.schemas.utils import random_lower_string


def test_connection(
    configurations: tuple[IdentityProviderCreateExtended, Openstack, Project],
) -> None:
    """Connection creation always succeeds, it is its usage that may fail."""
    (idp, provider_conf, project) = configurations
    region_name = random_lower_string()
    token = random_lower_string()

    conn = connect_to_provider(
        provider_conf=provider_conf,
        idp=idp,
        project_id=project.id,
        region_name=region_name,
        token=token,
    )
    assert conn.auth.get("auth_url") == provider_conf.auth_url
    assert conn.auth.get("identity_provider") == idp.relationship.idp_name
    assert conn.auth.get("protocol") == idp.relationship.protocol
    assert conn.auth.get("access_token") == token
    assert conn.auth.get("project_id") == project.id
    assert conn._compute_region == region_name
