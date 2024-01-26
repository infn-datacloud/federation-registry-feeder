from subprocess import CompletedProcess
from unittest.mock import patch
from uuid import uuid4

import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, Issuer, UserGroup
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@case(tags=["user_groups"])
@parametrize(with_user_groups=[0, 1, 2])
def case_with_user_groups(with_user_groups: int) -> int:
    return with_user_groups


@pytest.fixture
def sla() -> SLA:
    """Fixture with an SLA without projects."""
    start_date, end_date = random_start_end_dates()
    return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


@pytest.fixture
def user_group(sla: SLA) -> UserGroup:
    """Fixture with an UserGroup without projects."""
    return UserGroup(name=random_lower_string(), slas=[sla])


@patch("src.models.identity_provider.subprocess.run")
def test_identity_provider_schema(mock_cmd, user_group: UserGroup) -> None:
    """Create a UserGroup with or without SLAs."""
    endpoint = random_url()
    token_from_container = random_lower_string()
    mock_cmd.return_value = CompletedProcess(
        args=["docker", "exec", random_lower_string(), "oidc-token", endpoint],
        returncode=0,
        stdout=token_from_container,
    )
    d = {
        "issuer": endpoint,
        "group_claim": random_lower_string(),
        "user_groups": [user_group],
    }
    item = Issuer(**d)
    assert item.endpoint == d.get("issuer")
    assert item.group_claim == d.get("group_claim")
    assert len(item.user_groups) == len(d.get("user_groups"))
    assert item.user_groups[0] == user_group
    assert item.token == token_from_container


@patch("src.models.identity_provider.subprocess.run")
@parametrize_with_cases("with_user_groups", cases=".", has_tag="user_groups")
def test_identity_provider_invalid_schema(
    mock_cmd, user_group: UserGroup, with_user_groups: bool
) -> None:
    """Create a UserGroup with or without SLAs."""
    endpoint = random_url()
    token_from_container = random_lower_string()
    mock_cmd.return_value = CompletedProcess(
        args=["docker", "exec", random_lower_string(), "oidc-token", endpoint],
        returncode=0,
        stdout=token_from_container,
    )
    d = {
        "issuer": endpoint,
        "group_claim": random_lower_string(),
    }
    if with_user_groups == 0:
        d["user_groups"] = None
    elif with_user_groups == 1:
        d["user_groups"] = []
    elif with_user_groups == 2:
        d["user_groups"] = [user_group, user_group]
    with pytest.raises(ValueError):
        Issuer(**d)


def test_identity_provider_no_token(user_group: UserGroup) -> None:
    """Create a UserGroup with or without SLAs."""
    endpoint = random_url()
    d = {
        "issuer": endpoint,
        "group_claim": random_lower_string(),
        "user_groups": [user_group],
    }
    with pytest.raises(ValueError):
        Issuer(**d)
