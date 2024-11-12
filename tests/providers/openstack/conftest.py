from logging import getLogger
from unittest.mock import patch

import pytest

from src.models.identity_provider import Issuer
from src.models.provider import Openstack
from src.providers.openstack import OpenstackData
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    openstack_dict,
    project_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_lower_string


@pytest.fixture
def openstack_item():
    provider_conf = Openstack(
        **openstack_dict(),
        identity_providers=[auth_method_dict()],
        projects=[project_dict()],
    )
    issuer = Issuer(
        **issuer_dict(),
        token=random_lower_string(),
        user_groups=[{**user_group_dict(), "slas": [{**sla_dict()}]}],
    )
    logger = getLogger("test")
    with patch("src.providers.openstack.OpenstackData.retrieve_info"):
        item = OpenstackData(provider_conf=provider_conf, issuer=issuer, logger=logger)
    return item
