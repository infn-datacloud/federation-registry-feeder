from logging import getLogger
from unittest.mock import patch

import pytest
from fed_reg.provider.schemas_extended import IdentityProviderCreateExtended

from src.models.provider import Openstack, Project
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    openstack_dict,
    project_dict,
    random_lower_string,
)


@pytest.fixture
def openstack_item(identity_provider_create: IdentityProviderCreateExtended):
    project_conf = Project(**project_dict())
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_conf],
    )
    region_name = random_lower_string()
    token = random_lower_string()
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        item = OpenstackData(
            provider_conf=provider_conf,
            project_conf=project_conf,
            identity_provider=identity_provider_create,
            region_name=region_name,
            token=token,
            logger=logger,
        )
    return item
