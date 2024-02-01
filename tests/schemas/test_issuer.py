from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import pytest
from pytest_cases import parametrize_with_cases

from src.models.identity_provider import Issuer, UserGroup
from tests.schemas.utils import random_lower_string, random_url


class CaseInvalidUserGroups:
    def case_none(self) -> None:
        return None

    def case_empty_list(self) -> List[UserGroup]:
        return []

    def case_duplicated_user_groups(self, user_group: UserGroup) -> List[UserGroup]:
        return [user_group, user_group]


def issuer_dict() -> Dict[str, Any]:
    """Dict with Issuer minimal attributes."""
    return {"issuer": random_url(), "group_claim": random_lower_string()}


@patch(
    "src.models.identity_provider.subprocess.run",
    return_value=Mock(returncode=0, stdout=random_lower_string()),
)
def test_identity_provider_schema(mock_cmd: Mock, user_group: UserGroup) -> None:
    """Valid Issuer schema with one UserGroup.

    Patch call to subprocess.run to return a mock token string.
    """
    d = issuer_dict()
    d["user_groups"] = [user_group]
    item = Issuer(**d)
    mock_cmd.assert_called_once()
    assert item.endpoint == d.get("issuer")
    assert item.group_claim == d.get("group_claim")
    assert len(item.user_groups) == len(d.get("user_groups"))
    assert item.user_groups[0] == user_group
    assert item.token == mock_cmd.return_value.stdout.strip("\n")


@patch(
    "src.models.identity_provider.subprocess.run",
    return_value=Mock(returncode=0, stdout=random_lower_string()),
)
@parametrize_with_cases("user_groups", cases=CaseInvalidUserGroups)
def test_identity_provider_invalid_schema(
    mock_cmd: Mock, user_groups: Optional[List[UserGroup]]
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
    mock_cmd.assert_called_once()


@patch(
    "src.models.identity_provider.subprocess.run",
    return_value=Mock(returncode=1, stdout=random_lower_string()),
)
def test_identity_provider_no_token(mock_cmd: Mock, user_group: UserGroup) -> None:
    """Invalid Issuer schema.

    Patch call to subprocess.run to return a failed execution."""
    d = issuer_dict()
    d["user_groups"] = [user_group]
    with pytest.raises(ValueError):
        Issuer(**d)
    mock_cmd.assert_called_once()
