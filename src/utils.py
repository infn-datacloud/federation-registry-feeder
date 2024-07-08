import os
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import Dict, List, Optional, Tuple

import yaml
from fed_reg.provider.schemas_extended import ProviderCreateExtended

from src.config import Settings, URLs
from src.crud import CRUD
from src.logger import create_logger
from src.models.config import SiteConfig


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


def get_conf_files(*, settings: Settings, logger: Logger) -> List[str]:
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


def load_config(
    *, fname: str, log_level: str | int | None = None
) -> Optional[SiteConfig]:
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
        except ValueError as e:
            logger.error(e)
            return None
    else:
        logger.error("Empty configuration")
        return None


def get_site_configs(
    *, yaml_files: List[str], log_level: str | int | None = None
) -> tuple[List[SiteConfig], bool]:
    """Create a list of SiteConfig from a list of yaml files."""
    with ThreadPoolExecutor() as executor:
        site_configs = executor.map(
            lambda x: load_config(fname=x, log_level=log_level), yaml_files
        )
    return list(filter(lambda x: x is not None, site_configs)), any(
        [x is None for x in site_configs]
    )


def get_read_write_headers(*, token: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """From an access token, create the read and write headers."""
    read_header = {"authorization": f"Bearer {token}"}
    write_header = {
        **read_header,
        "accept": "application/json",
        "content-type": "application/json",
    }
    return (read_header, write_header)


def update_database(
    *,
    service_api_url: URLs,
    items: List[ProviderCreateExtended],
    token: str,
    logger: Logger,
) -> bool:
    """Update the Federation-Registry data.

    Create the read and write headers to use in requests.
    Retrieve current providers.
    For each current federated provider, if a provider with the same name and type
    already exists, update it, otherwise create a new provider entry with the given
    data. Once all the current federated providers have been added or updated, remove
    the remaining providers retrieved from the Federation-Registry, they are no more
    tracked.

    Return True if no errors happened otherwise False.
    """
    read_header, write_header = get_read_write_headers(token=token)
    crud = CRUD(
        url=service_api_url.providers,
        read_headers=read_header,
        write_headers=write_header,
        logger=logger,
    )

    logger.info("Retrieving data from Federation-Registry")
    db_items = {db_item.name: db_item for db_item in crud.read()}
    for item in items:
        db_item = db_items.pop(item.name, None)
        if db_item is None or db_item.type != item.type:
            crud.create(data=item)
        else:
            crud.update(new_data=item, old_data=db_item)
    for db_item in db_items.values():
        crud.remove(item=db_item)

    return crud.error
