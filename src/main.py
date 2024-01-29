import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List

from app.provider.schemas_extended import ProviderCreateExtended

from src.config import get_settings
from src.logger import logger
from src.models.identity_provider import Issuer
from src.models.provider import Openstack
from src.providers.core import get_provider
from src.utils import (
    get_conf_files,
    infer_service_endpoints,
    load_config,
    update_database,
)

MAX_WORKERS = 7
data_lock = Lock()


def add_os_provider_to_list(
    os_conf: Openstack,
    trusted_idps: List[Issuer],
    providers: List[ProviderCreateExtended],
):
    """Add Openstack providers to the provider lists."""
    provider = get_provider(os_conf=os_conf, trusted_idps=trusted_idps)
    with data_lock:
        providers.append(provider)


if __name__ == "__main__":
    providers = []
    thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    logger.setLevel(logging.DEBUG)

    # Load Federation Registry configuration, infer Federation Registry endpoints and
    # read all yaml files containing providers configurations.
    settings = get_settings()
    fed_reg_endpoints = infer_service_endpoints(settings=settings)
    yaml_files = get_conf_files(settings=settings)

    # Multithreading read.
    config = None
    for file in yaml_files:
        config = load_config(fname=file)
        if config:
            for os_conf in config.openstack:
                thread_pool.submit(
                    add_os_provider_to_list,
                    os_conf=os_conf,
                    trusted_idps=config.trusted_idps,
                    providers=providers,
                )
    thread_pool.shutdown(wait=True)

    # Update the Federation Registry
    if config:
        update_database(
            service_api_url=fed_reg_endpoints,
            token=config.trusted_idps[0].token,
            items=providers,
        )
