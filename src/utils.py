import os
from concurrent.futures import ThreadPoolExecutor
from logging import Logger

import yaml
from liboidcagent.liboidcagent import OidcAgentConnectError, OidcAgentError

from src.logger import create_logger
from src.models.config import Settings, URLs
from src.models.site_config import SiteConfig


def infer_service_endpoints(*, settings: Settings, logger: Logger) -> URLs:
    """Detect Federation-Registry endpoints from given configuration."""
    logger.info("Building Federation-Registry endpoints from configuration.")
    logger.debug("%r", settings)
    d = {}
    for k, v in settings.api_ver.dict().items():
        d[k.lower()] = os.path.join(settings.FED_REG_API_URL, f"{v}", f"{k.lower()}")
    endpoints = URLs(**d)
    logger.info("Federation-Registry endpoints detected")
    logger.debug("%r", endpoints)
    return endpoints


def get_conf_files(*, settings: Settings, logger: Logger) -> list[str]:
    """Get the list of the yaml files with the provider configurations."""
    logger.info("Detecting yaml files with provider configurations.")
    file_extension = ".config.yaml"
    yaml_files = filter(
        lambda x: x.endswith(file_extension), os.listdir(settings.PROVIDERS_CONF_DIR)
    )
    yaml_files = [os.path.join(settings.PROVIDERS_CONF_DIR, i) for i in yaml_files]
    logger.info("Files retrieved")
    logger.debug(yaml_files)
    return yaml_files


def load_config(*, fname: str, log_level: str | int | None = None) -> SiteConfig | None:
    """Load provider configuration from yaml file."""
    logger = create_logger(f"Yaml file {fname}", level=log_level)
    logger.info("Loading provider configuration from file")
    with open(fname) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    if config:
        try:
            config = SiteConfig(**config)
            logger.info("Configuration loaded")
            logger.debug("%r", config)
            return config
        except (ValueError, OidcAgentConnectError, OidcAgentError) as e:
            logger.error(e)
            return None
    else:
        logger.error("Empty configuration")
        return None


def get_site_configs(
    *, yaml_files: list[str], log_level: str | int | None = None
) -> tuple[list[SiteConfig], bool]:
    """Create a list of SiteConfig from a list of yaml files."""
    with ThreadPoolExecutor() as executor:
        site_configs = executor.map(
            lambda x: load_config(fname=x, log_level=log_level), yaml_files
        )
    return list(filter(lambda x: x is not None, site_configs)), any(
        [x is None for x in site_configs]
    )
