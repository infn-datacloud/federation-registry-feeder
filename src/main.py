"""Population script."""

from src.config import get_settings
from src.core import create_clients, retrieve_data_from_providers
from src.kafka_conn import Producer
from src.loaders.fed_mgr import load_connections_from_fed_mgr
from src.loaders.yaml_files import load_connections_from_yaml_files
from src.logger import create_logger
from src.parser import parser
from src.utils import filter_connections_with_valid_token


def main(log_level: str) -> None:
    """Main function.

    Based on settings, retrieve the list of site configurations from a list of YAML
    files or contacting the federation-manager service.

    Based on provider type, create a client object for each provider-region-project
    triplet and retrieve resources (limits, usage, flavors, images and networks).
    If the connection with a provider fails, do not interrupt the script.

    Send to kafka a message for each triplet with the relevant data.
    """
    error = False
    settings = get_settings()
    logger = create_logger(settings.APP_NAME, level=log_level)

    # Retrieve configurations from YAML files or fed-mgr
    if settings.FED_MGR_ENABLE:
        connections = load_connections_from_fed_mgr(base_url=settings.FED_MGR_URL)
    else:
        connections = load_connections_from_yaml_files(
            settings.PROVIDERS_CONF_DIR, logger=logger
        )

    filtered_connections = filter_connections_with_valid_token(
        connections, settings=settings, logger=logger
    )
    error = error or len(filtered_connections) != len(connections)

    # Retrieve data from providers
    clients = create_clients(filtered_connections, logger=logger)
    success_clients = retrieve_data_from_providers(
        clients, multithreading=settings.MULTITHREADING, logger=logger
    )
    error = error or len(clients) != len(success_clients)

    # Create kafka producer if needed and send data to kafka
    if settings.KAFKA_ENABLE:
        producer = Producer(settings=settings, logger=logger)
        success = producer.send(clients=clients)
        error = error or not success

    if error:
        logger.error("Found at least one error.")
        exit(1)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.loglevel.upper())
