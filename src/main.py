from concurrent.futures import ThreadPoolExecutor

from src.config import get_settings
from src.logger import create_logger
from src.parser import parser
from src.providers.core import ProviderThread
from src.utils import (
    get_conf_files,
    get_site_configs,
    infer_service_endpoints,
    update_database,
)


def main(log_level: str) -> None:
    """Main function.

    - Read yaml files
    - Organize data
    - Connect to federated provider and retrieve resources
    - Update Federation-Registry
    """
    logger = create_logger("Federation-Registry-Feeder", level=log_level)
    settings = get_settings()

    # Read all yaml files containing providers configurations.
    yaml_files = get_conf_files(settings=settings, logger=logger)
    site_configs = get_site_configs(yaml_files=yaml_files, log_level=log_level)

    # Prepare data (merge issuers and provider configurations)
    prov_iss_list = []
    for config in site_configs:
        prov_configs = [*config.openstack, *config.kubernetes]
        issuers = config.trusted_idps
        prov_iss_list: list[ProviderThread] = []
        for conf in prov_configs:
            prov_iss_list.append(
                ProviderThread(provider_conf=conf, issuers=issuers, log_level=log_level)
            )

    # Multithreading read
    providers = []
    with ThreadPoolExecutor() as executor:
        providers = executor.map(lambda x: x.get_provider(), prov_iss_list)
    providers = list(filter(lambda x: x, providers))

    # Update the Federation-Registry
    token = site_configs[0].trusted_idps[0].token if len(site_configs) > 0 else ""
    fed_reg_endpoints = infer_service_endpoints(settings=settings, logger=logger)
    update_database(
        service_api_url=fed_reg_endpoints, token=token, items=providers, logger=logger
    )


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.loglevel.upper())
