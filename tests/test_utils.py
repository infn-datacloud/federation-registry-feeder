import os
from pathlib import Path
from subprocess import CompletedProcess
from typing import List
from unittest.mock import patch
from uuid import uuid4

import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.config import APIVersions, Settings
from src.models.config import SiteConfig
from src.models.identity_provider import SLA, Issuer, UserGroup
from src.utils import (
    get_conf_files,
    get_read_write_headers,
    get_site_configs,
    infer_service_endpoints,
    load_config,
)
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    os.environ.clear()


@pytest.fixture
def sla() -> SLA:
    """Fixture with an SLA without projects."""
    start_date, end_date = random_start_end_dates()
    return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


@pytest.fixture
def user_group(sla: SLA) -> UserGroup:
    """Fixture with an UserGroup without projects."""
    return UserGroup(name=random_lower_string(), slas=[sla])


@pytest.fixture
def issuer(user_group: UserGroup) -> Issuer:
    return Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        user_groups=[user_group],
    )


@pytest.fixture
def config(issuer: Issuer) -> SiteConfig:
    return SiteConfig(trusted_idps=[issuer])


@case(tags=["fname"])
@parametrize(fname=["valid_provider", "invalid_provider", "empty_provider"])
def case_conf_fname(fname: str) -> str:
    return fname


@case(tags=["site_configs"])
@parametrize(num_items=[0, 1])
def case_yaml_files(num_items: int) -> List[str]:
    return [str(i) for i in range(num_items)]


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
@parametrize_with_cases("fname", cases=".", has_tag="fname")
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


@patch("src.utils.load_config")
@parametrize_with_cases("yaml_files", cases=".", has_tag="site_configs")
def test_no_site_configs(mock_load_conf, yaml_files: List[str]) -> None:
    mock_load_conf.return_value = None
    site_configs = get_site_configs(yaml_files=yaml_files)
    assert len(site_configs) == 0


@patch("src.utils.load_config")
def test_get_site_configs(mock_load_conf, config: SiteConfig) -> None:
    yaml_files = ["test"]
    mock_load_conf.return_value = config
    site_configs = get_site_configs(yaml_files=yaml_files)
    assert len(site_configs) == len(yaml_files)


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
