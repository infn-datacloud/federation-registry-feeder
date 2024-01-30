import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import AuthMethod
from tests.schemas.utils import random_lower_string, random_url


@parametrize(attr=["name", "endpoint"])
def case_missing_attr(attr: str) -> str:
    return attr


def test_auth_method_schema() -> None:
    d = {
        "name": random_lower_string(),
        "protocol": random_lower_string(),
        "endpoint": random_url(),
    }
    item = AuthMethod(**d)
    assert item.idp_name == d.get("name")
    assert item.protocol == d.get("protocol")
    assert item.endpoint == d.get("endpoint")


@parametrize_with_cases("missing_attr", cases=".")
def test_auth_method_invalid_schema(missing_attr: str) -> None:
    d = {"protocol": random_lower_string()}
    if missing_attr != "name":
        d["name"] = random_lower_string()
    elif missing_attr != "endpoint":
        d["endpoint"] = random_url()
    with pytest.raises(ValueError):
        AuthMethod(**d)
