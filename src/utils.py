import os
from typing import Dict, List, Tuple

import yaml
from app.provider.schemas_extended import ProviderCreateExtended
from config import Settings, URLs
from crud import CRUD
from logger import logger
from models.provider import SiteConfig


def infer_service_endpoints(*, settings: Settings) -> URLs:
    """Detect Federation Registry endpoints from given configuration."""
    logger.info("Building Federation Registry endpoints from configuration.")
    d = {}
    for k, v in settings.api_ver.dict().items():
        d[k.lower()] = os.path.join(
            settings.FEDERATION_REGISTRY_URL, "api", f"{v}", f"{k.lower()}"
        )
    return URLs(**d)


def load_config(*, fname: str) -> SiteConfig:
    """Load provider configuration from yaml file."""
    logger.info(f"Loading provider configuration from {fname}")
    with open(fname) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        config = SiteConfig(**config)

    logger.info("Configuration loaded")
    logger.debug(f"{config!r}")
    return config


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
    *, federation_registry_urls: URLs, items: List[ProviderCreateExtended], token: str
) -> None:
    """Use the read and write headers to create, update or remove providers from the
    Federation Registry.
    """
    read_header, write_header = get_read_write_headers(token=token)
    crud = CRUD(
        url=federation_registry_urls.providers,
        read_headers=read_header,
        write_headers=write_header,
    )

    logger.info("Retrieving data from Federation Registry")
    db_items = {db_item.name: db_item for db_item in crud.read(with_conn=True)}
    for item in items:
        db_item = db_items.pop(item.name, None)
        if db_item is None:
            crud.create(data=item)
        else:
            crud.update(new_data=item, old_data=db_item)
    for db_item in db_items.values():
        crud.remove(item=db_item)
