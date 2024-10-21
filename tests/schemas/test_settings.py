from random import randint
from typing import Literal

import pytest
from pydantic import AnyHttpUrl, ValidationError
from pytest_cases import parametrize, parametrize_with_cases

from src.models.config import APIVersions, Settings
from tests.utils import random_url


class CaseVersionKey:
    @parametrize(key=APIVersions.__fields__.keys())
    def case_api_version_key(self, key: str) -> str:
        return key


class CaseSettings:
    def case_fed_reg_url(self) -> tuple[Literal["FED_REG_API_URL"], AnyHttpUrl]:
        return "FED_REG_API_URL", random_url()

    def case_vol_labels_single(
        self,
    ) -> tuple[Literal["BLOCK_STORAGE_VOL_LABELS"], list[str]]:
        return "BLOCK_STORAGE_VOL_LABELS", ["first"]

    def case_vol_labels_multiple(
        self,
    ) -> tuple[Literal["BLOCK_STORAGE_VOL_LABELS"], list[str]]:
        return "BLOCK_STORAGE_VOL_LABELS", ["a", "b"]

    def case_conf_dir(
        self,
    ) -> tuple[Literal["PROVIDERS_CONF_DIR"], Literal["/test/path"]]:
        return "PROVIDERS_CONF_DIR", "/test/path"

    def case_oidc_agent_container(
        self,
    ) -> tuple[Literal["OIDC_AGENT_CONTAINER_NAME"], Literal["test-container-name"]]:
        return "OIDC_AGENT_CONTAINER_NAME", "test-container-name"


class CaseInvalidSettings:
    def case_fed_reg_url_empty_string(
        self,
    ) -> tuple[Literal["FED_REG_API_URL"], Literal[""]]:
        return "FED_REG_API_URL", ""

    def case_fed_reg_url_non_url(
        self,
    ) -> tuple[Literal["FED_REG_API_URL"], Literal["test.wrong.url.it"]]:
        return "FED_REG_API_URL", "test.wrong.url.it"

    def case_oidc_agent_container_empty_string(
        self,
    ) -> tuple[Literal["OIDC_AGENT_CONTAINER_NAME"], Literal[""]]:
        return "OIDC_AGENT_CONTAINER_NAME", ""


def test_api_versions_defaults() -> None:
    """APIVersions does not need an initial value."""
    api_ver = APIVersions()
    for v in api_ver.dict().values():
        assert v == "v1"


@parametrize_with_cases("key", cases=CaseVersionKey)
def test_api_versions_single_attr(key: str) -> None:
    """Each APIVersions key works correctly."""
    d = {key: f"v{randint(2,10)}"}
    api_ver = APIVersions(**d)
    for k, v in api_ver.dict().items():
        assert v == d[key] if k == key else v == "v1"


@parametrize_with_cases("key", cases=CaseVersionKey)
def test_api_versions_invalid_attr(key: str) -> None:
    """Check APIVersions is case sensitive."""
    d = {key.lower(): f"v{randint(2,10)}"}
    with pytest.raises(ValidationError):
        APIVersions(**d)


def test_settings_defaults() -> None:
    """Settings needs at least an APIVersions instance to work."""
    api_ver = APIVersions()
    settings = Settings(api_ver=api_ver)
    assert settings.FED_REG_API_URL == "http://localhost:8000/api"
    assert settings.BLOCK_STORAGE_VOL_LABELS == []
    assert settings.PROVIDERS_CONF_DIR == "providers-conf"
    assert settings.OIDC_AGENT_CONTAINER_NAME is None
    assert settings.FED_REG_TIMEOUT == 30
    assert settings.KAFKA_HOSTNAME is None
    assert settings.KAFKA_TOPIC is None
    assert settings.api_ver == api_ver


@parametrize_with_cases("key, value", cases=CaseSettings)
def test_settings_single_attr(key: str, value: str) -> None:
    d = {key: value}
    settings = Settings(api_ver=APIVersions(), **d)
    assert settings.__getattribute__(key) == value


def test_settings_empty_conf_dir_path() -> None:
    settings = Settings(api_ver=APIVersions(), PROVIDERS_CONF_DIR="")
    assert settings.PROVIDERS_CONF_DIR == "."


@parametrize_with_cases("key, value", cases=CaseInvalidSettings)
def test_settings_invalid_attr(key: str, value: str) -> None:
    """Check APIVersions is case sensitive."""
    d = {key: value}
    with pytest.raises(ValidationError):
        Settings(api_ver=APIVersions(), **d)
