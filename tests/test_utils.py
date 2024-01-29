import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from pytest_cases import parametrize, parametrize_with_cases

from src.config import APIVersions, Settings
from src.utils import (
    get_conf_files,
    get_read_write_headers,
    infer_service_endpoints,
    load_config,
)
from tests.schemas.utils import random_lower_string, random_url


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    os.environ.clear()


@parametrize(fname=["valid_provider", "invalid_provider", "empty_provider"])
def case_conf_fname(fname: str) -> str:
    return fname


def test_infer_fed_reg_urls() -> None:
    """Verify fed-reg endpoints detection.

    Inferred urls are made up combining the fed-reg base url, api version and target
    entity (lower case).
    """
    settings = Settings(api_ver=APIVersions())
    endpoints = infer_service_endpoints(settings=settings)
    for k, v in endpoints.dict().items():
        version = settings.api_ver.__getattribute__(k.upper())
        assert v == os.path.join(settings.FED_REG_API_URL, f"{version}", f"{k}")


def test_conf_file_retrieval(tmp_path: Path) -> None:
    """Load yaml files from target folder.

    Discard files with wrong extension.
    """
    d = tmp_path / "configs"
    d.mkdir()
    fnames = ["empty.config.yaml", "empty.config.yml", "empty.yaml", "empty.yml"]
    for fname in fnames:
        f = d / fname
        f.write_text("")
    settings = Settings(api_ver=APIVersions(), PROVIDERS_CONF_DIR=d)
    yaml_files = get_conf_files(settings=settings)
    assert len(yaml_files) == 1
    assert yaml_files[0] == os.path.join(settings.PROVIDERS_CONF_DIR, fnames[0])


def test_invalid_conf_dir() -> None:
    """Invalid conf dir."""
    settings = Settings(api_ver=APIVersions(), PROVIDERS_CONF_DIR="invalid_path")
    with pytest.raises(FileNotFoundError):
        get_conf_files(settings=settings)


@patch("src.models.identity_provider.subprocess.run")
@parametrize_with_cases("fname", cases=".")
def test_load_config_yaml(mock_cmd, fname: str) -> None:
    """Load provider configuration from yaml file."""
    mock_cmd.return_value = CompletedProcess(
        args=["docker", "exec", random_lower_string(), "oidc-token", random_url()],
        returncode=0,
        stdout=random_lower_string(),
    )
    fpath = f"tests/configs/{fname}.config.yaml"
    config = load_config(fname=fpath)
    assert config if fname == "valid_provider" else not config


def test_load_config_yaml_invalid_path() -> None:
    """Load provider configuration from yaml file."""
    with pytest.raises(FileNotFoundError):
        load_config(fname="invalid_path")


def test_load_config_yaml_invalid_yaml(tmp_path: Path) -> None:
    """Load provider configuration from yaml file."""
    fname = tmp_path / "test.config.yaml"
    fname.write_text("")
    assert not load_config(fname=fname)


def test_headers_creation() -> None:
    token = "test"
    (read, write) = get_read_write_headers(token=token)
    assert read
    assert write
    assert "authorization" in read.keys()
    assert read["authorization"] == f"Bearer {token}"
    assert "authorization" in write.keys()
    assert write["authorization"] == f"Bearer {token}"
    assert write["content-type"] == "application/json"


# TODO
# def test_update_db() -> None:
#     pass
