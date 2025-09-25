"""Functions to read YAML files with the configurations of the federated providers."""

import os
from logging import Logger
from pathlib import Path
from typing import Any

import yaml.parser
from fed_mgr.v1.providers.schemas import ProviderType
from pydantic import ValidationError

from src.config import Settings
from src.exceptions import AbortProcedureError, InvalidYamlError
from src.loaders.utils import complete_partial_connection, create_partial_connection
from src.models.site_config import SiteConfig
from src.models.yml import IdentityProvider, Provider, YamlConfig


def load_files(path: Path, *, logger: Logger) -> list[str]:
    """Get the list of the yaml files with the provider configurations.

    Args:
        path (Path): path to the directory with the yaml files with the configurations.
        logger (Logger): Logger instance.

    Returns:
        list of str: List of yaml files.

    Raises:
        AbortProcedureError if the directory is not a valid path.

    """
    msg = f"Detecting yaml files with provider configurations in folder: {path}"
    logger.info(msg)

    try:
        yaml_files = filter(lambda x: x.endswith((".yaml", ".yml")), os.listdir(path))
    except (FileNotFoundError, NotADirectoryError) as e:
        msg = f"No directory named: {path}"
        logger.error(msg)
        raise AbortProcedureError(msg) from e

    yaml_files = [os.path.join(path, i) for i in yaml_files]
    logger.info("Files retrieved")
    logger.debug(yaml_files)
    return yaml_files


def read_config(fname: str, *, logger: Logger) -> YamlConfig:
    """Load provider configuration from yaml file.

    Empty files are ignored. Error during YAML parsing does not interrupt the procedure

    Args:
        fname (str): path to the directory with the yaml files with the configurations.
        logger (Logger): Logger instance.

    Returns:
        list of str: List of yaml files.

    Raises:
        InvalidYamlError when the YAML file does not exist, or is not parsable.

    """
    msg = f"Loading provider configuration from file: {fname}"
    logger.info(msg)

    try:
        with open(fname) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError as e:
        msg = f"Error reading file {fname}"
        logger.error(msg)
        raise InvalidYamlError(msg) from e
    except yaml.parser.ParserError as e:
        msg = f"Error parsing file {fname}"
        logger.error(msg)
        raise InvalidYamlError(msg) from e

    if not config:  # empty string/file
        msg = "Empty configuration. Ignoring"
        logger.warning(msg)
        raise InvalidYamlError(msg)

    try:
        return YamlConfig(**config)
    except ValidationError as e:
        msg = f"Invalid YAML file: {e!r}"
        logger.error(msg)
        raise InvalidYamlError(msg) from e


def complete_partial_connections(
    partial_connections: dict[str, dict[str, Any]], idps: list[IdentityProvider]
) -> list[SiteConfig]:
    """Read partial connections and retrieve details from trusted idps.

    For each project of an sla of a user group of an idp, retrieve the correspondin
    partial connection (if present) and populate the idp info. Add each new connection
    to the input list.

    Args:
        idps (list of IdentityProvider): list of trusted identity providers.
        partial_connections (dict of {str: dict}): partial connections. The key is the
            project's ID and the value is another dict. These one has the idp endpoint
            as key and the idp data as value

    Returns:
        list of Connections:

    """
    connections = []
    for idp in idps:
        groups = idp.user_groups
        for group in groups:
            slas = group.slas
            for sla in slas:
                conn_params = partial_connections.pop(sla.name, None)
                if conn_params is not None:
                    conn_params["user_group"] = group.name
                    conn = complete_partial_connection(conn_params, idp.endpoint)
                    connections.append(conn)
    return connections


def list_conn_params_from_providers(
    providers: list[Provider],
    trusted_idps: list[IdentityProvider],
    *,
    settings: Settings,
) -> list[SiteConfig]:
    """From the list of providers retrieve the list of connection parameters.

    Args:
        providers (list of Provider): list of provider's configuration
        trusted_idps (list of IdentityProvider): list of trusted identity providers
        settings (Settings): application settings

    Returns:
        (list of SiteConfig, dict): tuple with the list of connections and a dict with
            the project id and the partial connection parameters.

    """
    partial_connections = {}

    for provider in providers:
        idps = provider.identity_providers
        regions = provider.regions
        projects = provider.projects
        ca_path = None
        if provider.type == ProviderType.kubernetes and provider.ca_fname is not None:
            ca_path = os.path.join(settings.CA_DIR, provider.ca_fname)
        for project in projects:
            for region in regions:
                kwargs = {
                    "provider_name": provider.name,
                    "provider_type": provider.type,
                    "provider_endpoint": provider.auth_endpoint,
                    "image_tags": provider.image_tags,
                    "network_tags": provider.network_tags,
                    "region_name": region.name,
                    "overbooking_cpu": region.overbooking_cpu,
                    "overbooking_ram": region.overbooking_ram,
                    "bandwidth_in": region.bandwidth_in,
                    "bandwidth_out": region.bandwidth_out,
                    "project_id": project.id,
                    "default_public_net": project.default_public_net,
                    "default_private_net": project.default_private_net,
                    "ca_path": ca_path,
                }
                if project.private_net_proxy is not None:
                    kwargs["private_net_proxy_host"] = project.private_net_proxy.host
                    kwargs["private_net_proxy_user"] = project.private_net_proxy.user

                # If the provider support multiple idps, an intersection between the
                # project and the authorized user group is needed to detect the correct
                # idp. Anyway, an intersection is needed to detect the matching user
                # group.
                data = create_partial_connection(idps=idps, **kwargs)
                partial_connections[project.sla] = data

    connections = complete_partial_connections(partial_connections, trusted_idps)

    return connections


def load_connections_from_yaml_files(
    path: Path, *, settings: Settings, logger: Logger
) -> list[SiteConfig]:
    """Retrieve the list of connections from YAML files.

    Read the folder content and parse the yaml files content.

    Args:
        path (Path): path to the directory with the yaml files with the configurations.
        settings (Settings): Application settings.
        logger (Logger): Logger instance.

    Returns:
        list(Connections): list of connection parameters

    Raises:
        AbortProcedureError if the directory is not a valid path (forwarded from
        'load_files' function).

    """
    error = False
    yaml_configs: list[YamlConfig] = []
    yaml_files = load_files(path, logger=logger)
    for fname in yaml_files:
        try:
            config = read_config(fname, logger=logger)
            yaml_configs.append(config)
        except InvalidYamlError:
            error = True
    if error:
        logger.error("Not all YAML files have been loaded.")

    connections = []
    for config in yaml_configs:
        connections += list_conn_params_from_providers(
            config.openstack + config.kubernetes, config.trusted_idps, settings=settings
        )

    return connections
