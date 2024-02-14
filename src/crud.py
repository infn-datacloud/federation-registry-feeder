import os
from typing import Any, Dict, List, Optional

import requests
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fed_reg.provider.schemas_extended import (
    ProviderCreateExtended,
    ProviderRead,
    ProviderReadExtended,
)
from pydantic import AnyHttpUrl, BaseModel, Field, validator

from src.logger import logger

TIMEOUT = 30  # s


class CRUD(BaseModel):
    multi_url: AnyHttpUrl = Field(alias="url")
    read_headers: Dict[str, str]
    write_headers: Dict[str, str]
    single_url: Optional[AnyHttpUrl]

    @validator("single_url", pre=True, always=True)
    @classmethod
    def build_single_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        return os.path.join(values.get("multi_url"), "{uid}")

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
        elif resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            logger.error(f"Provider={data.name} has not been created.")
            logger.error(f"{resp.json()}")
            return None

        logger.debug(f"Status code: {resp.status_code}")
        logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def remove(self, *, item: ProviderRead) -> None:
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
        elif resp.status_code == status.HTTP_304_NOT_MODIFIED:
            logger.info(
                f"New data match stored data. Provider={new_data.name} not modified"
            )
            return None
        elif resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            logger.error(f"Provider={new_data.name} has not been updated.")
            logger.error(f"{resp.json()}")
            return None

        logger.debug(f"Status code: {resp.status_code}")
        logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()
