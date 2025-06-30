from concurrent.futures import ThreadPoolExecutor

from src.fed_reg_conn import update_database
from src.kafka_conn import get_kafka_prod
from src.logger import create_logger
from src.models.config import get_settings
from src.parser import parser
from src.providers.core import ProviderThread
from src.utils import (
    create_provider,
    get_conf_files,
    get_site_configs,
    infer_service_endpoints,
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
        providers_data = executor.map(lambda x: x.get_provider(), pthreads)
    providers_data = list(providers_data)
    providers_data = list(filter(lambda x: x, providers_data))
    error |= any([x.error for x in pthreads])

    providers = []
    kafka_data = []
    for provider_conf, connections_data, error in providers_data:
        kafka_data += [i.to_dict() for i in connections_data]
        provider = create_provider(
            provider_conf=provider_conf, connections_data=connections_data, error=error
        )
        providers.append(provider)

    # Create kafka producer if needed and send data to kafka
    if settings.KAFKA_ENABLE and settings.KAFKA_BOOTSTRAP_SERVERS is not None:
        kafka_prod = get_kafka_prod(settings=settings, logger=logger)
        kafka_prod.send(
            topic=settings.KAFKA_TOPIC,
            data=kafka_data,
            msg_version=settings.KAFKA_MSG_VERSION,
        )

    # Update the Federation-Registry
    token = site_configs[0].trusted_idps[0].token if len(site_configs) > 0 else ""
    fedreg_endpoints = infer_service_endpoints(settings=settings, logger=logger)
    error |= not update_database(
        service_api_url=fedreg_endpoints,
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
