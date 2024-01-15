import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List

from app.provider.schemas_extended import ProviderCreateExtended
from logger import logger
from models.provider import Openstack, TrustedIDP
from providers.opnstk import get_provider
from utils import load_config, load_service_endpoints, update_database

from src.config import get_settings

MAX_WORKERS = 7
data_lock = Lock()


def add_os_provider_to_list(
    os_conf: Openstack,
    trusted_idps: List[TrustedIDP],
    providers: List[ProviderCreateExtended],
):
    """Add Openstack providers to the provider lists."""
    provider = get_provider(os_conf=os_conf, trusted_idps=trusted_idps)
    with data_lock:
        providers.append(provider)


if __name__ == "__main__":
    base_path = "."
    logger.setLevel(logging.DEBUG)

    # Load Federation Registry configuration
    config = get_settings()
    logger.debug(f"{config!r}")

    fed_reg_endpoints = load_service_endpoints(config=config)

    providers = []
    thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    # Read all yaml files containing providers configurations.
    # Multithreading read.
    yaml_files = list(
        filter(lambda x: x.endswith(".config.yaml"), os.listdir(base_path))
    )
    for file in yaml_files:
        config = load_config(fname=file)
        for os_conf in config.openstack:
            thread_pool.submit(
                add_os_provider_to_list,
                os_conf=os_conf,
                trusted_idps=config.trusted_idps,
                providers=providers,
            )
    thread_pool.shutdown(wait=True)

    # Update the Federation Registry
    update_database(
        federation_registry_urls=fed_reg_endpoints,
        token=config.trusted_idps[0].token,
        items=providers,
    )
