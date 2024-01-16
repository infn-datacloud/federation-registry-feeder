import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List

from app.provider.schemas_extended import ProviderCreateExtended
from config import get_settings
from logger import logger
from models.provider import Openstack, TrustedIDP
from providers.opnstk import get_provider
from utils import infer_service_endpoints, load_config, update_database

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
    file_extension = ".config.yaml"
    providers = []
    thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    logger.setLevel(logging.DEBUG)

    # Load Federation Registry configuration, infer Federation Registry endpoints and
    # read all yaml files containing providers configurations.
    settings = get_settings()
    fed_reg_endpoints = infer_service_endpoints(settings=settings)
    yaml_files = filter(
        lambda x: x.endswith(file_extension),
        os.listdir(settings.PROVIDERS_CONF_DIR),
    )
    yaml_files = [os.path.join(settings.PROVIDERS_CONF_DIR, i) for i in yaml_files]

    logger.debug(f"{settings!r}")
    logger.debug(f"{fed_reg_endpoints!r}")
    logger.debug(f"{yaml_files}")

    # Multithreading read.
    config = None
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
    if config:
        update_database(
            federation_registry_urls=fed_reg_endpoints,
            token=config.trusted_idps[0].token,
            items=providers,
        )
