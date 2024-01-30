from random import randint
from typing import Any, List, Literal, Tuple

import pytest
from pydantic import ValidationError
from pytest_cases import case, parametrize, parametrize_with_cases

from src.config import APIVersions, Settings


@case(tags=["api_ver"])
@parametrize(key=APIVersions.__fields__.keys())
def case_api_version_key(key: str) -> str:
    return key


class CaseSettings:
    def case_fed_reg_url(
        self,
    ) -> Tuple[Literal["FED_REG_API_URL"], Literal["http://test.url.it/api"]]:
        return "FED_REG_API_URL", "http://test.url.it/api"

    def case_vol_labels_single(
        self,
    ) -> Tuple[Literal["BLOCK_STORAGE_VOL_LABELS"], List[str]]:
        return "BLOCK_STORAGE_VOL_LABELS", ["first"]

    def case_vol_labels_multiple(
        self,
    ) -> Tuple[Literal["BLOCK_STORAGE_VOL_LABELS"], List[str]]:
        return "BLOCK_STORAGE_VOL_LABELS", ["a", "b"]

    def case_conf_dir(
        self,
    ) -> Tuple[Literal["PROVIDERS_CONF_DIR"], Literal["/test/path"]]:
        return "PROVIDERS_CONF_DIR", "/test/path"

    def case_oidc_agent_container(
        self,
    ) -> Tuple[Literal["OIDC_AGENT_CONTAINER_NAME"], Literal["test-container-name"]]:
        return "OIDC_AGENT_CONTAINER_NAME", "test-container-name"


class CaseInvalidSettings:
    def case_fed_reg_url_empty_string(
        self,
    ) -> Tuple[Literal["FED_REG_API_URL"], Literal[""]]:
        return "FED_REG_API_URL", ""

    def case_fed_reg_url_non_url(
        self,
    ) -> Tuple[Literal["FED_REG_API_URL"], Literal["test.wrong.url.it"]]:
        return "FED_REG_API_URL", "test.wrong.url.it"

    def case_oidc_agent_container_empty_string(
        self,
    ) -> Tuple[Literal["OIDC_AGENT_CONTAINER_NAME"], Literal[""]]:
        return "OIDC_AGENT_CONTAINER_NAME", ""


def test_api_versions_defaults() -> None:
    """APIVersions does not need an initial value."""
    api_ver = APIVersions()
    for v in api_ver.dict().values():
        assert v == "v1"


@parametrize_with_cases("key", cases=".", has_tag="api_ver")
def test_api_versions_single_attr(key: str) -> None:
    """Each APIVersions key works correctly."""
    d = {key: f"v{randint(2,10)}"}
    api_ver = APIVersions(**d)
    for k, v in api_ver.dict().items():
        assert v == d[key] if k == key else v == "v1"


@parametrize_with_cases("key", cases=".", has_tag="api_ver")
def test_api_versions_invalid_attr(key: str) -> None:
    """Check APIVersions is case sensitive."""
    d = {key.lower(): f"v{randint(2,10)}"}
    with pytest.raises(ValidationError):
        APIVersions(**d)


def test_settings_defaults(api_ver: APIVersions) -> None:
    """Settings needs at least an APIVersions instance to work."""
    settings = Settings(api_ver=api_ver)
    assert settings.FED_REG_API_URL == "http://localhost:8000/api"
    assert settings.BLOCK_STORAGE_VOL_LABELS == []
    assert settings.PROVIDERS_CONF_DIR == "providers-conf"
    assert settings.OIDC_AGENT_CONTAINER_NAME == "feeder-dev-oidc-agent"
    assert settings.api_ver == api_ver


@parametrize_with_cases("key, value", cases=CaseSettings)
def test_settings_single_attr(api_ver: APIVersions, key: str, value: Any) -> None:
    d = {key: value}
    settings = Settings(api_ver=api_ver, **d)
    assert settings.__getattribute__(key) == value


def test_settings_empty_conf_dir_path(api_ver: APIVersions) -> None:
    settings = Settings(api_ver=api_ver, PROVIDERS_CONF_DIR="")
    assert settings.PROVIDERS_CONF_DIR == "."


@parametrize_with_cases("key, value", cases=CaseInvalidSettings)
def test_settings_invalid_attr(api_ver: APIVersions, key: str, value: Any) -> None:
    """Check APIVersions is case sensitive."""
    d = {key: value}
    with pytest.raises(ValidationError):
        Settings(api_ver=api_ver, **d)
