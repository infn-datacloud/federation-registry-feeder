import os
from logging import Logger

import requests
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fed_reg.provider.schemas_extended import (
    ProviderCreateExtended,
    ProviderRead,
    ProviderReadExtended,
)
from pydantic import AnyHttpUrl

from src.models.config import Settings


class CRUD:
    """Class with create read update and delete operations.

    Each operation makes a call to the Federation-Registry.
    """

    def __init__(
        self,
        *,
        url: AnyHttpUrl,
        read_headers: dict[str, str],
        write_headers: dict[str, str],
        logger: Logger,
        settings: Settings,
    ) -> None:
        self.multi_url = url
        self.single_url = os.path.join(self.multi_url, "{uid}")
        self.read_headers = read_headers
        self.write_headers = write_headers
        self.logger = logger
        self.timeout = settings.FED_REG_TIMEOUT
        self.error = False

    def read(self) -> list[ProviderRead]:
        """Retrieve all providers from the Federation-Registry."""
        self.logger.info("Looking for all Providers")
        self.logger.debug("Url=%s", self.multi_url)

        resp = requests.get(
            url=self.multi_url, headers=self.read_headers, timeout=self.timeout
        )
        if resp.status_code == status.HTTP_200_OK:
            self.logger.info("Retrieved")
            self.logger.debug(resp.json())
            return [ProviderRead(**i) for i in resp.json()]

        self.error = True
        self.logger.debug("Status code: %s", resp.status_code)
        self.logger.debug("Message: %s", resp.text)
        resp.raise_for_status()

    def create(self, *, data: ProviderCreateExtended) -> ProviderReadExtended:
        """Create new instance."""
        self.logger.info("Creating Provider=%s", data.name)
        self.logger.debug("Url=%s", self.multi_url)
        self.logger.debug("New Data=%s", data)

        resp = requests.post(
            url=self.multi_url,
            json=jsonable_encoder(data),
            headers=self.write_headers,
            timeout=self.timeout,
        )
        if resp.status_code == status.HTTP_201_CREATED:
            self.logger.info("Provider=%s created", data.name)
            self.logger.debug(resp.json())
            return ProviderReadExtended(**resp.json())
        elif resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            self.logger.error("Provider=%s has not been created.", data.name)
            self.logger.error(resp.json())
            self.error = True
            return None

        self.error = True
        self.logger.debug("Status code: %s", resp.status_code)
        self.logger.debug("Message: %s", resp.text)
        resp.raise_for_status()

    def remove(self, *, item: ProviderRead) -> None:
        """Remove item."""
        self.logger.info("Removing Provider=%s", item.name)
        self.logger.debug("Url=%s", self.single_url.format(uid=item.uid))

        resp = requests.delete(
            url=self.single_url.format(uid=item.uid),
            headers=self.write_headers,
            timeout=self.timeout,
        )
        if resp.status_code == status.HTTP_204_NO_CONTENT:
            self.logger.info("Provider=%s removed", item.name)
            return None

        self.error = True
        self.logger.debug("Status code: %s", resp.status_code)
        self.logger.debug("Message: %s", resp.text)
        resp.raise_for_status()

    def update(
        self, *, new_data: ProviderCreateExtended, old_data: ProviderRead
    ) -> ProviderReadExtended | None:
        """Update existing instance."""
        self.logger.info("Updating Provider=%s.", new_data.name)
        self.logger.debug("Url=%s", self.single_url.format(uid=old_data.uid))
        self.logger.debug("New Data=%s", new_data)

        resp = requests.put(
            url=self.single_url.format(uid=old_data.uid),
            json=jsonable_encoder(new_data),
            headers=self.write_headers,
            timeout=self.timeout,
        )
        if resp.status_code == status.HTTP_200_OK:
            self.logger.info("Provider=%s updated", new_data.name)
            self.logger.debug(resp.json())
            return ProviderReadExtended(**resp.json())
        elif resp.status_code == status.HTTP_304_NOT_MODIFIED:
            self.logger.info(
                "New data match stored data. Provider=%s not modified", new_data.name
            )
            return None
        elif resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            self.logger.error("Provider=%s has not been updated.", new_data.name)
            self.logger.error(resp.json())
            self.error = True
            return None

        self.error = True
        self.logger.debug("Status code: %s", resp.status_code)
        self.logger.debug("Message: %s", resp.text)
        resp.raise_for_status()
