import logging
from concurrent.futures import ThreadPoolExecutor

from src.config import get_settings
from src.logger import logger
from src.providers.core import get_provider
from src.utils import (
    get_conf_files,
    get_site_configs,
    infer_service_endpoints,
    update_database,
)


def main() -> None:
    # Load Federation Registry configuration, infer Federation Registry endpoints and
    # read all yaml files containing providers configurations.
    settings = get_settings()
    yaml_files = get_conf_files(settings=settings)
    site_configs = get_site_configs(yaml_files=yaml_files)

    # Multithreading read.
    providers = []
    for config in site_configs:
        with ThreadPoolExecutor() as executor:
            prov_configs = [*config.openstack, *config.kubernetes]
            issuers = config.trusted_idps
            prov_iss_list = [
                {"provider_conf": conf, "issuers": issuers} for conf in prov_configs
            ]
            providers = executor.map(lambda x: get_provider(**x), prov_iss_list)
            providers = list(filter(lambda x: x, providers))

    # Update the Federation Registry
    token = site_configs[0].trusted_idps[0].token if len(site_configs) > 0 else ""
    fed_reg_endpoints = infer_service_endpoints(settings=settings)
    update_database(service_api_url=fed_reg_endpoints, token=token, items=providers)


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    main()
