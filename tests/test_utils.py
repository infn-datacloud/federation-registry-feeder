import os
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.config import Settings
from src.models.config import SiteConfig
from src.utils import (
    get_conf_files,
    get_read_write_headers,
    get_site_configs,
    infer_service_endpoints,
    load_config,
)
from tests.schemas.utils import random_lower_string


class CaseYamlFiles:
    @case(tags=["num-items"])
    @parametrize(num_items=[0, 1])
    def case_yaml_files(self, num_items: int) -> List[str]:
        return [str(i) for i in range(num_items)]

    @case(tags=["fname"])
    @parametrize(fname=["valid_provider", "invalid_provider", "empty_provider"])
    def case_conf_fname(self, fname: str) -> str:
        return fname


def test_infer_fed_reg_urls(settings: Settings) -> None:
    """Verify fed-reg endpoints detection.

    Inferred urls are made up combining the fed-reg base url, api version and target
    entity (lower case).
    """
    endpoints = infer_service_endpoints(settings=settings)
    for k, v in endpoints.dict().items():
        version = settings.api_ver.__getattribute__(k.upper())
        assert v == os.path.join(settings.FED_REG_API_URL, f"{version}", f"{k}")


def test_conf_file_retrieval(tmp_path: Path, settings: Settings) -> None:
    """Load yaml files from target folder.

    Discard files with wrong extension.
    """
    d = tmp_path / "configs"
    d.mkdir()
    fnames = ["empty.config.yaml", "empty.config.yml", "empty.yaml", "empty.yml"]
    for fname in fnames:
        f = d / fname
        f.write_text("")
    settings.PROVIDERS_CONF_DIR = d
    yaml_files = get_conf_files(settings=settings)
    assert len(yaml_files) == 1
    assert yaml_files[0] == os.path.join(settings.PROVIDERS_CONF_DIR, fnames[0])


def test_invalid_conf_dir(settings: Settings) -> None:
    """Invalid conf dir."""
    settings.PROVIDERS_CONF_DIR = "invalid_path"
    with pytest.raises(FileNotFoundError):
        get_conf_files(settings=settings)

@patch(
    "src.models.identity_provider.retrieve_token", return_value=random_lower_string()
)
@parametrize_with_cases("fname", cases=CaseYamlFiles, has_tag="fname")
def test_load_config_yaml(mock_cmd: Mock, fname: str) -> None:
    """Load provider configuration from yaml file."""
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
@parametrize_with_cases("yaml_files", cases=CaseYamlFiles, has_tag="num-items")
def test_no_site_configs(mock_load_conf: Mock, yaml_files: List[str]) -> None:
    mock_load_conf.return_value = None
    site_configs = get_site_configs(yaml_files=yaml_files)
    assert len(site_configs) == 0


@patch("src.utils.load_config")
def test_get_site_configs(mock_load_conf: Mock, site_config: SiteConfig) -> None:
    yaml_files = ["test"]
    mock_load_conf.return_value = site_config
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
