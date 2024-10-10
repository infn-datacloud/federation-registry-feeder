import os
from unittest.mock import Mock, patch

import pytest
from liboidcagent.liboidcagent import OidcAgentConnectError, OidcAgentError
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer, UserGroup, retrieve_token
from tests.schemas.utils import (
    issuer_dict,
    random_lower_string,
    random_url,
    sla_dict,
    user_group_dict,
)


class CaseInvalidUserGroups:
    def case_none(self) -> None:
        return None

    def case_empty_list(self) -> list[UserGroup]:
        return []

    def case_duplicated_user_groups(self) -> list[UserGroup]:
        item1 = UserGroup(**user_group_dict(), slas=[sla_dict()])
        item2 = UserGroup(
            **{**user_group_dict(), "name": item1.name}, slas=[sla_dict()]
        )
        return [item1, item2]


@patch(
    "src.models.identity_provider.retrieve_token", return_value=random_lower_string()
)
def test_identity_provider_schema(mock_token: Mock) -> None:
    """Valid Issuer schema with one UserGroup.

    Patch call to subprocess.run to return a mock token string.
    """
    d = issuer_dict()
    d["user_groups"] = [UserGroup(**user_group_dict(), slas=[sla_dict()])]
    item = Issuer(**d)
    mock_token.assert_called_once()
    assert item.endpoint == d.get("issuer")
    assert item.group_claim == d.get("group_claim")
    assert len(item.user_groups) == len(d.get("user_groups"))
    assert item.user_groups[0] == d.get("user_groups")[0]
    assert item.token == mock_token.return_value.strip("\n")


@patch(
    "src.models.identity_provider.retrieve_token", return_value=random_lower_string()
)
@parametrize_with_cases("user_groups", cases=CaseInvalidUserGroups)
def test_identity_provider_invalid_schema(
    mock_token: Mock, user_groups: list[UserGroup] | None
) -> None:
    """Invalid Issuer schema.

    Patch call to subprocess.run to return a mock token string.

    The UserGroup list contains duplicated UserGroup values, or it is an empty list, or
    it received a None value. None value: if the slas key is omitted as in the previous
    test, by default it is an empty list.
    """
    d = issuer_dict()
    d["user_groups"] = user_groups
    with pytest.raises(ValueError):
        Issuer(**d)
    mock_token.assert_called_once()


@patch("src.models.identity_provider.retrieve_token", return_value=ValueError)
def test_identity_provider_no_token(mock_token: Mock) -> None:
    """Invalid Issuer schema.

    Patch call to subprocess.run to return a failed execution."""
    d = issuer_dict()
    d["user_groups"] = [UserGroup(**user_group_dict(), slas=[sla_dict()])]
    with pytest.raises(ValueError):
        Issuer(**d)
    mock_token.assert_called_once()


# Retrieve token


@patch(
    "src.models.identity_provider.get_settings",
    return_value=Mock(OIDC_AGENT_CONTAINER_NAME="test"),
)
@patch(
    "src.models.identity_provider.subprocess.run",
    return_value=Mock(returncode=0, stdout=random_lower_string()),
)
def test_retrieve_token_with_container(mock_subprocess_cmd: Mock, mock_settings: Mock):
    assert retrieve_token(random_url()) is not None


@patch(
    "src.models.identity_provider.get_settings",
    return_value=Mock(OIDC_AGENT_CONTAINER_NAME="test"),
)
@patch(
    "src.models.identity_provider.subprocess.run",
    return_value=Mock(returncode=1, stdout=random_lower_string()),
)
def test_container_not_found(mock_subprocess_cmd: Mock, mock_settings: Mock):
    with pytest.raises(ValueError):
        retrieve_token(random_lower_string())


def test_env_oidc_sock_not_set():
    """Variabile OIDC_SOCK is not set."""
    with pytest.raises(OidcAgentConnectError):
        retrieve_token(random_lower_string())


def test_oidc_agent_not_running():
    """Variable is set but the agent is not running."""
    os.environ.setdefault("OIDC_SOCK", random_lower_string())
    with pytest.raises(OidcAgentError):
        retrieve_token(random_lower_string())


@patch(
    "src.models.identity_provider.get_access_token_by_issuer_url",
    return_value=random_lower_string(),
)
def test_retrieve_token_with_local_oidc(mock_liboidc: Mock):
    """Mock response from liboidcagent function returning token."""
    os.environ.setdefault("OIDC_SOCK", random_lower_string())
    retrieve_token(random_lower_string())
