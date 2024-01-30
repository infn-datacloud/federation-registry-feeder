import os
from pathlib import Path
from subprocess import CompletedProcess
from typing import List
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.provider.schemas_extended import ProviderCreateExtended, ProviderReadExtended
from fastapi.encoders import jsonable_encoder
from pytest_cases import case, parametrize, parametrize_with_cases

from src.config import APIVersions, Settings, URLs
from src.models.config import SiteConfig
from src.models.identity_provider import Issuer
from src.utils import (
    get_conf_files,
    get_read_write_headers,
    get_site_configs,
    infer_service_endpoints,
    load_config,
    update_database,
)
from tests.schemas.utils import random_lower_string, random_provider_type, random_url


@pytest.fixture(autouse=True)
def clear_os_environment() -> None:
    os.environ.clear()


@pytest.fixture
def provider_urls() -> URLs:
    base_url = random_url()
    return URLs(**{k: os.path.join(base_url, k) for k in URLs.__fields__.keys()})


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


@patch("src.crud.requests.get")
def test_do_nothing_to_db(mock_get: Mock, provider_urls: URLs) -> None:
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([])
    update_database(
        service_api_url=provider_urls, items=[], token=random_lower_string()
    )


@patch("src.crud.requests.post")
@patch("src.crud.requests.get")
def test_add_provider_to_db(
    mock_get: Mock, mock_post: Mock, provider_urls: URLs
) -> None:
    new_provider = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    created_provider = ProviderReadExtended(uid=uuid4(), **new_provider.dict())
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([])
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = jsonable_encoder(created_provider)
    update_database(
        service_api_url=provider_urls, items=[new_provider], token=random_lower_string()
    )


@patch("src.crud.requests.delete")
@patch("src.crud.requests.get")
def test_delete_provider_from_db(
    mock_get: Mock, mock_del: Mock, provider_urls: URLs
) -> None:
    provider = ProviderReadExtended(
        uid=uuid4(),
        name=random_lower_string(),
        type=random_provider_type(),
        identity_providers=[],
        projects=[],
        regions=[],
    )
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([provider])
    mock_del.return_value.status_code = 204
    update_database(
        service_api_url=provider_urls, items=[], token=random_lower_string()
    )


@patch("src.crud.requests.put")
@patch("src.crud.requests.get")
def test_update_provider_in_db(
    mock_get: Mock, mock_put: Mock, provider_urls: URLs
) -> None:
    old_provider = ProviderReadExtended(
        uid=uuid4(),
        name=random_lower_string(),
        type=random_provider_type(),
        identity_providers=[],
        projects=[],
        regions=[],
    )
    new_provider = ProviderCreateExtended(
        name=old_provider.name, type=old_provider.type
    )
    updated_provider = ProviderReadExtended(uid=old_provider.uid, **new_provider.dict())
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([old_provider])
    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = jsonable_encoder([updated_provider])
    update_database(
        service_api_url=provider_urls, items=[new_provider], token=random_lower_string()
    )
