import os
from typing import Dict, List, Optional

import requests
from app.provider.schemas_extended import (
    ProviderCreateExtended,
    ProviderRead,
    ProviderReadExtended,
)
from fastapi import status
from fastapi.encoders import jsonable_encoder
from pydantic import AnyHttpUrl

from src.logger import logger

TIMEOUT = 30  # s


class CRUD:
    def __init__(
        self,
        *,
        url: AnyHttpUrl,
        read_headers: Dict[str, str],
        write_headers: Dict[str, str],
    ) -> None:
        self.read_headers = read_headers
        self.write_headers = write_headers
        self.multi_url = url
        self.single_url = os.path.join(url, "{uid}")

    def read(self) -> List[ProviderRead]:
        """Retrieve all providers from the Federation-Registry."""
        logger.info("Looking for all Providers")
        logger.debug(f"Url={self.multi_url}")

        resp = requests.get(
            url=self.multi_url, headers=self.read_headers, timeout=TIMEOUT
        )
        if resp.status_code == status.HTTP_200_OK:
            logger.info("Retrieved")
            logger.debug(f"{resp.json()}")
            return [ProviderRead(**i) for i in resp.json()]

        logger.debug(f"Status code: {resp.status_code}")
        logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def create(self, *, data: ProviderCreateExtended) -> ProviderReadExtended:
        """Create new instance."""
        logger.info(f"Creating Provider={data.name}")
        logger.debug(f"Url={self.multi_url}")
        logger.debug(f"New Data={data}")

        resp = requests.post(
            url=self.multi_url,
            json=jsonable_encoder(data),
            headers=self.write_headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == status.HTTP_201_CREATED:
            logger.info(f"Provider={data.name} created")
            logger.debug(f"{resp.json()}")
            return ProviderReadExtended(**resp.json())

        logger.debug(f"Status code: {resp.status_code}")
        logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def remove(self, *, item: ProviderReadExtended) -> None:
        """Remove item."""
        logger.info(f"Removing Provider={item.name}.")
        logger.debug(f"Url={self.single_url.format(uid=item.uid)}")

        resp = requests.delete(
            url=self.single_url.format(uid=item.uid),
            headers=self.write_headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == status.HTTP_204_NO_CONTENT:
            logger.info(f"Provider={item.name} removed")
            return None

        logger.debug(f"Status code: {resp.status_code}")
        logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def update(
        self, *, new_data: ProviderCreateExtended, old_data: ProviderRead
    ) -> Optional[ProviderReadExtended]:
        """Update existing instance."""
        logger.info(f"Updating Provider={new_data.name}.")
        logger.debug(f"Url={self.single_url.format(uid=old_data.uid)}")
        logger.debug(f"New Data={new_data}")

        resp = requests.put(
            url=self.single_url.format(uid=old_data.uid),
            json=jsonable_encoder(new_data),
            headers=self.write_headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == status.HTTP_200_OK:
            logger.info(f"Provider={new_data.name} updated")
            logger.debug(f"{resp.json()}")
            return ProviderReadExtended(**resp.json())

        if resp.status_code == status.HTTP_304_NOT_MODIFIED:
            logger.info(
                f"New data match stored data. Provider={new_data.name} not modified"
            )
            return None

        logger.debug(f"Status code: {resp.status_code}")
        logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()
