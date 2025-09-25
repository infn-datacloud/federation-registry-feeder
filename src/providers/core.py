"""Client base class."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from fed_mgr.v1.providers.schemas import ProviderType
from pydantic import AnyHttpUrl

from src.logger import create_logger


class ProviderClient(ABC):
    """Class to organize data retrieved from and Openstack instance."""

    def __init__(
        self,
        *,
        provider_name: str,
        provider_endpoint: AnyHttpUrl,
        provider_type: ProviderType,
        project_id: str,
        idp_endpoint: AnyHttpUrl,
        idp_name: str,
        idp_token: str,
        user_group: str,
        logger_name: str,
        log_level: int = logging.INFO,
        timeout: int = 2,
    ) -> None:
        """Create an openstack client to retrieve data."""
        self.provider_name = provider_name
        self.provider_endpoint = str(provider_endpoint)
        self.provider_type = provider_type
        self.project_id = project_id
        self.idp_endpoint = str(idp_endpoint)
        self.idp_name = idp_name
        self.idp_token = idp_token
        self.user_group = user_group
        self.timeout = timeout
        self.logger = create_logger(logger_name, log_level)

    @abstractmethod
    def create_connection(self) -> Any:
        """Create connection to Openstack provider.

        Returns:
            Any: provider connection instance.

        """

    @abstractmethod
    def retrieve_info(self) -> bool:
        """Connect to the provider e retrieve information.

        Returns:
            bool: True if the operation succeeded. False otherwise.

        """
