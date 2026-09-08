from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.fed_reg_conn import update_database
from src.kafka_conn import send_to_kafka
from src.logger import create_logger, get_error_details, start_error_capture
from src.models.config import get_settings
from src.parser import parser
from src.providers.core import ProviderThread
from src.utils import (
    create_provider,
    get_conf_files,
    get_site_configs,
    infer_service_endpoints,
)


def update_error_state(error_details: str, state_file: str | Path) -> bool:
    """Persist changed error details and return whether this run should fail."""
    path = Path(state_file)
    previous_error = path.read_text() if path.exists() else ""

    if not error_details:
        if previous_error:
            path.write_text("")
        return False

    if error_details == previous_error:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(error_details)
    return True


def main(log_level: str) -> None:
    """Main function.

    - Read yaml files
    - Organize data
    - Connect to federated provider and retrieve resources
    - Update Federation-Registry
    """
    start_error_capture()
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
    if settings.PARALLEL:
        with ThreadPoolExecutor() as executor:
            providers_data = executor.map(lambda x: x.get_provider(), pthreads)
        providers_data = list(providers_data)
    else:
        providers_data = [p.get_provider(parallel=False) for p in pthreads]
    providers_data = list(filter(lambda x: x, providers_data))
    error |= any([x.error for x in pthreads])

    providers = []
    kafka_data = []
    for provider_conf, connections_data, provider_error in providers_data:
        kafka_data += [i.to_dict() for i in connections_data]
        provider = create_provider(
            provider_conf=provider_conf,
            connections_data=connections_data,
            error=provider_error,
        )
        providers.append(provider)

    # Create kafka producer if needed and send data to kafka
    if settings.KAFKA_ENABLE:
        send_to_kafka(settings=settings, logger=logger, data=kafka_data)

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

    error_details = get_error_details()
    if update_error_state(error_details, settings.ERROR_STATE_FILE):
        exit(1)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.loglevel.upper())
