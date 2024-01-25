from typing import Union
from unittest.mock import patch
from uuid import uuid4

from app.auth_method.schemas import AuthMethodBase
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.connection import ConnectFailure
from keystoneauth1.exceptions.http import NotFound, Unauthorized
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import Openstack, Project, TrustedIDP
from src.providers.openstack import connect_to_provider
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@parametrize(
    exception=[
        "invalid_url",
        "expired_token",
        "wrong_auth_type",
        "wrong_idp_name",
        "wrong_protocol",
        "invalid_project_id",
        "timeout",
    ]
)
def case_exception(
    exception: str,
) -> Union[ConnectFailure, Unauthorized, NoMatchingPlugin, NotFound]:
    if exception == "invalid_url" or exception == "timeout":
        return ConnectFailure()
    elif (
        exception == "expired_token"
        or exception == "wrong_protocol"
        or exception == "invalid_project_id"
    ):
        return Unauthorized()
    elif exception == "wrong_auth_type":
        return NoMatchingPlugin("fake")
    elif exception == "wrong_idp_name":
        return NotFound()


@patch("src.providers.openstack.connect")
@parametrize_with_cases("exception", cases=".")
def test_fail_connection(mock_func, exception) -> None:
    mock_func.side_effect = exception
    project_id = uuid4()
    start_date, end_date = random_start_end_dates()
    sla = SLA(
        doc_uuid=uuid4(),
        start_date=start_date,
        end_date=end_date,
        projects=[project_id],
    )
    user_group = UserGroup(name=random_lower_string(), slas=[sla])
    relationship = AuthMethodBase(
        idp_name=random_lower_string(), protocol=random_lower_string()
    )
    issuer = Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        relationship=relationship,
        user_groups=[user_group],
    )
    trusted_idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=relationship.idp_name,
        protocol=relationship.protocol,
    )
    project = Project(id=project_id, sla=sla.doc_uuid)
    provider_conf = Openstack(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[trusted_idp],
        projects=[project],
    )
    assert not connect_to_provider(
        provider_conf=provider_conf,
        idp=issuer,
        project_id=project.id,
        region_name=random_lower_string(),
    )
