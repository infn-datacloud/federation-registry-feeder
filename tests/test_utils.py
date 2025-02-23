import os
from logging import getLogger
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from liboidcagent.liboidcagent import OidcAgentConnectError, OidcAgentError
from pydantic import ValidationError
from pytest_cases import parametrize_with_cases

from src.models.config import APIVersions, Settings
from src.models.site_config import SiteConfig
from src.utils import (
    get_conf_files,
    get_site_configs,
    infer_service_endpoints,
    load_config,
)
from tests.schemas.utils import (
    auth_method_dict,
    issuer_dict,
    kubernetes_dict,
    openstack_dict,
    project_dict,
    region_dict,
    sla_dict,
    user_group_dict,
)
from tests.utils import random_float, random_lower_string


class CaseYamlFiles:
    def case_no_providers(self) -> dict[str, Any]:
        sla = sla_dict()
        issuer = issuer_dict()
        issuer["user_groups"] = [{**user_group_dict(), "slas": [sla]}]
        return {"trusted_idps": [issuer]}

    def case_openstack(self) -> dict[str, Any]:
        sla = sla_dict()
        issuer = issuer_dict()
        issuer["user_groups"] = [{**user_group_dict(), "slas": [sla]}]
        auth_method = auth_method_dict()
        auth_method["endpoint"] = issuer["issuer"]
        project = project_dict()
        project["sla"] = sla["doc_uuid"]
        provider = openstack_dict()
        provider["identity_providers"] = [auth_method]
        provider["projects"] = [project]
        return {"trusted_idps": [issuer], "openstack": [provider]}

    def case_k8s(self) -> dict[str, Any]:
        sla = sla_dict()
        issuer = issuer_dict()
        issuer["user_groups"] = [{**user_group_dict(), "slas": [sla]}]
        auth_method = auth_method_dict()
        auth_method["endpoint"] = issuer["issuer"]
        project = project_dict()
        project["sla"] = sla["doc_uuid"]
        provider = kubernetes_dict()
        provider["identity_providers"] = [auth_method]
        provider["projects"] = [project]
        return {"trusted_idps": [issuer], "kubernetes": [provider]}


class CaseSiteConfigError:
    def case_validation_error(self) -> type[ValidationError]:
        return ValidationError([], SiteConfig)

    def case_oidc_agent_conn_error(self) -> type[OidcAgentConnectError]:
        return OidcAgentConnectError(random_lower_string())

    def case_oidc_agent_error(self) -> type[OidcAgentError]:
        return OidcAgentError(random_lower_string())


class CaseOverbookingBandwidth:
    def case_overbooking_and_bandwidth(self) -> dict[str, Any]:
        sla = sla_dict()
        issuer = issuer_dict()
        issuer["user_groups"] = [{**user_group_dict(), "slas": [sla]}]
        auth_method = auth_method_dict()
        auth_method["endpoint"] = issuer["issuer"]
        project = project_dict()
        project["sla"] = sla["doc_uuid"]
        provider = openstack_dict()
        provider["identity_providers"] = [auth_method]
        provider["projects"] = [project]
        provider["regions"] = [region_dict()]
        provider["overbooking_cpu"] = random_float(0, 10)
        provider["overbooking_ram"] = random_float(0, 10)
        provider["bandwidth_in"] = random_float(0, 10)
        provider["bandwidth_out"] = random_float(0, 10)
        provider["regions"][0]["overbooking_cpu"] = random_float(0, 10)
        provider["regions"][0]["overbooking_ram"] = random_float(0, 10)
        provider["regions"][0]["bandwidth_in"] = random_float(0, 10)
        provider["regions"][0]["bandwidth_out"] = random_float(0, 10)
        return {"trusted_idps": [issuer], "openstack": [provider]}


def test_infer_fed_reg_urls() -> None:
    """Verify fed-reg endpoints detection.

    Inferred urls are made up combining the fed-reg base url, api version and target
    entity (lower case).
    """
    settings = Settings(api_ver=APIVersions())
    endpoints = infer_service_endpoints(settings=settings, logger=getLogger())
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
    settings = Settings(api_ver=APIVersions())
    settings.PROVIDERS_CONF_DIR = d

    yaml_files = get_conf_files(settings=settings, logger=getLogger())
    assert len(yaml_files) == 1
    assert yaml_files[0] == os.path.join(settings.PROVIDERS_CONF_DIR, fnames[0])


@patch("src.utils.os.listdir")
def test_invalid_conf_dir(mock_listdir: Mock) -> None:
    """Invalid conf dir."""
    mock_listdir.side_effect = FileNotFoundError
    settings = Settings(api_ver=APIVersions())
    settings.PROVIDERS_CONF_DIR = "invalid_path"
    yaml_files = get_conf_files(settings=settings, logger=getLogger())
    assert len(yaml_files) == 0


@parametrize_with_cases("yaml_content", cases=CaseYamlFiles)
@patch("src.models.identity_provider.retrieve_token")
@patch("src.utils.open")
@patch("src.utils.yaml.load")
def test_load_yaml(
    mock_yaml: Mock, mock_open: Mock, mock_token: Mock, yaml_content: dict[str, Any]
) -> None:
    """Load provider configuration from yaml file."""
    mock_yaml.return_value = yaml_content
    mock_token.return_value = random_lower_string()

    config = load_config(fname=random_lower_string())
    assert config


@parametrize_with_cases("yaml_content", cases=CaseOverbookingBandwidth)
@patch("src.models.identity_provider.retrieve_token")
@patch("src.utils.open")
@patch("src.utils.yaml.load")
def test_load_region_with_overbooking_and_bandwidth(
    mock_yaml: Mock, mock_open: Mock, mock_token: Mock, yaml_content: dict[str, Any]
) -> None:
    """Load provider configuration from yaml file."""
    mock_yaml.return_value = yaml_content
    mock_token.return_value = random_lower_string()

    config = load_config(fname=random_lower_string())
    assert config
    assert (
        config.openstack[0].regions[0].overbooking_cpu
        == yaml_content["openstack"][0]["regions"][0]["overbooking_cpu"]
    )
    assert (
        config.openstack[0].regions[0].overbooking_ram
        == yaml_content["openstack"][0]["regions"][0]["overbooking_ram"]
    )
    assert (
        config.openstack[0].regions[0].bandwidth_in
        == yaml_content["openstack"][0]["regions"][0]["bandwidth_in"]
    )
    assert (
        config.openstack[0].regions[0].bandwidth_out
        == yaml_content["openstack"][0]["regions"][0]["bandwidth_out"]
    )


@patch("src.utils.open")
def test_load_yaml_invalid_path(mock_open: Mock) -> None:
    """Load provider configuration from yaml file."""
    mock_open.side_effect = FileNotFoundError
    assert not load_config(fname="invalid_path")


@patch("src.models.identity_provider.retrieve_token")
@patch("src.utils.open")
@patch("src.utils.yaml.load")
def test_load_yaml_empty(mock_yaml: Mock, mock_open: Mock, mock_token: Mock) -> None:
    """Load provider configuration from yaml file."""
    mock_yaml.return_value = None
    mock_token.return_value = random_lower_string()
    assert not load_config(fname=random_lower_string())


@parametrize_with_cases("error", cases=CaseSiteConfigError)
@patch("src.models.site_config.SiteConfig.__init__")
@patch("src.models.identity_provider.retrieve_token")
@patch("src.utils.open")
@patch("src.utils.yaml.load")
def test_load_yaml_invalid_config(
    mock_yaml: Mock, mock_open: Mock, mock_token: Mock, mock_class: Mock, error: Any
) -> None:
    """Load provider configuration from yaml file."""
    sla = sla_dict()
    issuer = issuer_dict()
    issuer["user_groups"] = [{**user_group_dict(), "slas": [sla]}]
    mock_yaml.return_value = {"trusted_idps": [issuer]}
    mock_class.side_effect = error
    mock_token.return_value = random_lower_string()
    assert not load_config(fname=random_lower_string())


@patch("src.utils.load_config")
def test_no_site_configs(mock_load_conf: Mock) -> None:
    """Error when loading site config.

    Config with errors are not returned and error is True.
    """
    mock_load_conf.return_value = None
    site_configs, error = get_site_configs(yaml_files=["test"])
    assert len(site_configs) == 0
    assert error


@parametrize_with_cases("yaml_content", cases=CaseYamlFiles)
@patch("src.models.identity_provider.retrieve_token")
@patch("src.utils.load_config")
def test_get_site_configs(
    mock_load_conf: Mock, mock_token: Mock, yaml_content: dict[str, Any]
) -> None:
    mock_token.return_value = random_lower_string()
    mock_load_conf.return_value = SiteConfig(**yaml_content)
    site_configs, error = get_site_configs(yaml_files=["test"])
    assert len(site_configs) == 1
    assert not error
