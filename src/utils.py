"""Application utilities."""

import subprocess
from logging import Logger
from typing import Any

from liboidcagent import get_access_token_by_issuer_url
from liboidcagent.liboidcagent import OidcAgentConnectError, OidcAgentError
from pydantic import AnyHttpUrl

from src.config import Settings
from src.models.site_config import SiteConfig


def find_duplicates(items: list[Any], attr: str | None = None) -> list[Any]:
    """Find duplicate items in a list.

    Optionally filter items by attribute.

    Args:
        items (list of Any): List of items to inspects
        attr (str | None): Optional to key to use as reference for duplicate values in
            the list.

    Returns:
        list (Any): the original list.

    """
    if attr:
        values = [j.__getattribute__(attr) for j in items]
    else:
        values = items
    seen = set()
    dupes = [x for x in values if x in seen or seen.add(x)]
    if attr:
        msg = f"There are multiple items with identical {attr}: {','.join(dupes)}"
    else:
        msg = f"There are multiple identical items: {','.join(dupes)}"
    if not len(dupes) == 0:
        raise ValueError(msg)
    return items


def retrieve_token(
    endpoint: AnyHttpUrl, *, settings: Settings, audience: str | None = None
) -> str:
    """Retrieve token using OIDC-Agent.

    If the container name is set use perform a docker exec command, otherwise use a
    local instance.

    Args:
        endpoint (AnyHttpUrl): issuer endpoint.
        settings (Settings): application settings.
        audience (str | None): audience the token should be generated for.

    Returns:
        str: access token belonging to the service user for this identity provider

    Raises:
        ValueError when there is an error executing the subprocess
        OidcAgentConnectError when there is an error connecting to OIDC-agent
        OidcAgentError when there is an error retrieving the token

    """
    if settings.OIDC_AGENT_CONTAINER_NAME is not None:
        token_cmd = subprocess.run(
            [
                "docker",
                "exec",
                settings.OIDC_AGENT_CONTAINER_NAME,
                "oidc-token",
                f"--time={settings.TOKEN_MIN_VALID_PERIOD}",
                f"--aud={audience}",
                str(endpoint),
            ],
            capture_output=True,
            text=True,
        )
        if token_cmd.returncode > 0:
            raise ValueError(token_cmd.stderr if token_cmd.stderr else token_cmd.stdout)
        token = token_cmd.stdout.strip("\n")
        return token

    token = get_access_token_by_issuer_url(
        str(endpoint),
        min_valid_period=settings.TOKEN_MIN_VALID_PERIOD,
        audience=audience,
    )
    return token


def filter_connections_with_valid_token(
    connections: list[SiteConfig],
    *,
    settings: Settings,
    logger: Logger,
) -> list[SiteConfig]:
    """Filter connections using an idp without a valid token.

    For each identity provider retrieve the token and filter connections using an idp
    without a valid token.

    Args:
        connections (list of SiteConfig): connections to filter
        idps (list of AnyHttpUrl): retrieve a token for each of the listed idps.
        settings (Settings): Application settings
        logger (Logger): Logger instance

    Returns:
        list of SiteConfig: the filtered list of connections.

    """
    valid_connections = []
    tokens = {}
    failed = []
    for connection in connections:
        # Skipping connection with an invalid IDP
        if connection.idp_endpoint in failed:
            continue

        # Check a similar token has already been generated and re-use it
        token = tokens.get((connection.idp_endpoint, connection.idp_audience), None)
        if token is not None:
            connection.idp_token = token
            valid_connections.append(connection)
            continue

        # Retrieve a new token
        try:
            connection.idp_token = retrieve_token(
                connection.idp_endpoint,
                settings=settings,
                audience=connection.idp_audience,
            )
        except (OidcAgentConnectError, OidcAgentError, ValueError) as e:
            msg = "Failed to load account configuration for idp "
            msg += f"{connection.idp_endpoint}. Error is: {e!s}"
            logger.error(msg)
            failed.append(connection.idp_endpoint)

        if connection.idp_token is not None:
            tokens[(connection.idp_endpoint, connection.idp_audience)] = (
                connection.idp_token
            )
            valid_connections.append(connection)

    return valid_connections
