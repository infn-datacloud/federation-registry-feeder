from concurrent.futures import ThreadPoolExecutor

from src.fed_reg_conn import update_database
from src.kafka_conn import get_kafka_prod, send_kafka_messages
from src.logger import create_logger
from src.models.config import get_settings
from src.parser import parser
from src.providers.core import ProviderThread
from src.utils import get_conf_files, get_site_configs, infer_service_endpoints


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
    site_configs, error = get_site_configs(yaml_files=yaml_files, log_level=log_level)

    # Prepare data (merge issuers and provider configurations)
    pthreads: list[ProviderThread] = []
    for config in site_configs:
        prov_configs = [*config.openstack, *config.kubernetes]
        issuers = config.trusted_idps
        for conf in prov_configs:
            pthreads.append(
                ProviderThread(provider_conf=conf, issuers=issuers, log_level=log_level)
            )

    # Multithreading read
    providers = []
    with ThreadPoolExecutor() as executor:
        providers = executor.map(lambda x: x.get_provider(), pthreads)
    providers = list(providers)
    providers = list(filter(lambda x: x, providers))
    error |= any([x.error for x in pthreads])

    # Create kafka producer if needed
    kafka_prod = get_kafka_prod(
        hostname=settings.KAFKA_HOSTNAME, topic=settings.KAFKA_TOPIC, logger=logger
    )
    if kafka_prod is not None:
        # Send data to kafka
        send_kafka_messages(kafka_prod=kafka_prod, providers=providers)

    # Update the Federation-Registry
    token = site_configs[0].trusted_idps[0].token if len(site_configs) > 0 else ""
    fed_reg_endpoints = infer_service_endpoints(settings=settings, logger=logger)
    error |= not update_database(
        service_api_url=fed_reg_endpoints,
        token=token,
        items=providers,
        logger=logger,
        settings=settings,
    )

    if error:
        logger.error("Found at least one error.")
        exit(1)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.loglevel.upper())
