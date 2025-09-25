import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.models.provider import AuthMethod
from tests.schemas.utils import auth_method_dict


class CaseMissingAttr:
    @parametrize(attr=["endpoint"])
    def case_missing_attr(self, attr: str) -> str:
        return attr


def test_auth_method_schema() -> None:
    """Valid AuthMethod schema."""
    d = auth_method_dict()
    item = AuthMethod(**d)
    assert item.idp_name == d.get("name")
    assert item.protocol == d.get("protocol")
    assert item.endpoint == d.get("endpoint")


@parametrize_with_cases("missing_attr", cases=CaseMissingAttr)
def test_auth_method_invalid_schema(missing_attr: str) -> None:
    """Invalid AuthMethod schema.

    One of the mandatory arguments is missing.
    """
    d = auth_method_dict()
    d[missing_attr] = None
    with pytest.raises(ValueError):
        AuthMethod(**d)
