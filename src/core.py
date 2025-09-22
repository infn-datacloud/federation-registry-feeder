"""Resource providers clients management."""

from concurrent.futures import ThreadPoolExecutor
from logging import Logger

from fed_mgr.v1.providers.schemas import ProviderType

from src.models.site_config import SiteConfig
from src.providers.openstack import OpenstackClient


def create_clients(
    connections: list[SiteConfig], *, logger: Logger
) -> list[OpenstackClient]:
    """Generate a list of clients to connect to each trplet provider-region-project.

    Args:
        connections (list of SiteConfig): list of connections to open.
        logger (Logger): logger instance.

    Returns:
        list of clients: A client for each triplet.

    """
    clients = []
    for connection in connections:
        if connection.provider_type == ProviderType.openstack:
            msg = f"Creating openstack client: {connection.provider_name}-"
            msg += f"{connection.region_name}-{connection.project_id}"
            logger.info(msg)
            client = OpenstackClient(
                provider_name=connection.provider_name,
                provider_endpoint=connection.provider_endpoint,
                region_name=connection.region_name,
                project_id=connection.project_id,
                idp_endpoint=connection.idp_endpoint,
                idp_name=connection.idp_name,
                idp_protocol=connection.idp_protocol,
                idp_token=connection.idp_token,
                user_group=connection.user_group,
                image_tags=connection.image_tags,
                network_tags=connection.network_tags,
                overbooking_cpu=connection.overbooking_cpu,
                overbooking_ram=connection.overbooking_ram,
                bandwidth_in=connection.bandwidth_in,
                bandwidth_out=connection.bandwidth_out,
                default_public_net=connection.default_public_net,
                default_private_net=connection.default_private_net,
                private_net_proxy_host=connection.private_net_proxy_host,
                private_net_proxy_user=connection.private_net_proxy_user,
            )
            clients.append(client)
        elif connection.provider_type == ProviderType.kubernetes:
            msg = "Creating kubernetes client: "
            msg += f"{connection.provider_name}-{connection.project_id}"
            logger.info(msg)
            pass
    return clients


def retrieve_data_from_providers(
    clients: list[OpenstackClient],
    *,
    logger: Logger,
    multithreading: bool = False,
) -> list[OpenstackClient]:
    """For each client retrieve their resources.

    For each connection, create a separated thread (if multithreading mode is enabled)
    and try to connect to the provider.

    Args:
        clients (list of Client): list of clients. Open a connection for each of these.
        logger (Logger): logger instance.
        multithreading (bool): Enable multithreading mode.

    Returns:
        list of clients: Only the client that had successfully retrieved information.

    """
    success_clients = []
    if multithreading:
        logger.info("Multithreading mode enabled")
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(client.retrieve_info): client for client in clients
            }
            for future in futures:
                if future.result():
                    success_clients.append(futures[future])
    else:
        logger.info("Sequential mode enabled")
        for client in clients:
            success = client.retrieve_info()
            if success:
                success_clients.append(client)
    return success_clients
