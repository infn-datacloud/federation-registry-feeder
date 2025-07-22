from unittest.mock import Mock, patch

import pytest
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer, UserGroup, retrieve_token
from tests.schemas.utils import issuer_dict, sla_dict, user_group_dict
from tests.utils import random_lower_string


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
    assert item.client_id == d.get("client_id")
    assert item.client_secret == d.get("client_secret")


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


@patch("src.models.identity_provider.retrieve_token", side_effect=ValueError)
def test_identity_provider_no_token(mock_token: Mock) -> None:
    """Invalid Issuer schema.

    Patch call to subprocess.run to return a failed execution."""
    d = issuer_dict()
    d["user_groups"] = [UserGroup(**user_group_dict(), slas=[sla_dict()])]
    with pytest.raises(ValueError):
        Issuer(**d)
    mock_token.assert_called_once()


@patch("src.models.identity_provider.requests.get")
@patch("src.models.identity_provider.requests.post")
def test_retrieve_token_success(mock_post, mock_get):
    # Mock GET to introspection endpoint
    mock_get.return_value = Mock(
        status_code=200, json=lambda: {"token_endpoint": "https://example.com/token"}
    )
    # Mock POST to token endpoint
    mock_post.return_value = Mock(
        status_code=200, json=lambda: {"access_token": "test_token"}
    )
    token = retrieve_token(
        endpoint="https://example.com/", client_id="cid", client_secret="csecret"
    )
    assert token == "test_token"
    mock_get.assert_called_once()
    mock_post.assert_called_once()


@patch("src.models.identity_provider.requests.get")
def test_retrieve_token_introspection_fail(mock_get):
    mock_get.return_value = Mock(status_code=404)
    with pytest.raises(ValueError, match="Failed to contact introspection endpoint"):
        retrieve_token(
            endpoint="https://example.com/", client_id="cid", client_secret="csecret"
        )
    mock_get.assert_called_once()


@patch("src.models.identity_provider.requests.get")
@patch("src.models.identity_provider.requests.post")
def test_retrieve_token_token_fail(mock_post, mock_get):
    mock_get.return_value = Mock(
        status_code=200, json=lambda: {"token_endpoint": "https://example.com/token"}
    )
    mock_post.return_value = Mock(status_code=400)
    with pytest.raises(ValueError, match="Failed to retrieve token"):
        retrieve_token(
            endpoint="https://example.com/", client_id="cid", client_secret="csecret"
        )
    mock_get.assert_called_once()
    mock_post.assert_called_once()


@patch("src.models.identity_provider.requests.get")
@patch("src.models.identity_provider.requests.post")
def test_retrieve_token_no_access_token(mock_post, mock_get):
    mock_get.return_value = Mock(
        status_code=200, json=lambda: {"token_endpoint": "https://example.com/token"}
    )
    mock_post.return_value = Mock(status_code=200, json=lambda: {})
    token = retrieve_token(
        endpoint="https://example.com/", client_id="cid", client_secret="csecret"
    )
    assert token is None
