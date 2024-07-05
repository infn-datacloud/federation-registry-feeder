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

TIMEOUT = 30  # s


class CRUD(BaseModel):
    multi_url: AnyHttpUrl = Field(alias="url")
    read_headers: Dict[str, str]
    write_headers: Dict[str, str]
    single_url: Optional[AnyHttpUrl]
    logger: Any

    @validator("single_url", pre=True, always=True)
    @classmethod
    def build_single_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        return os.path.join(values.get("multi_url"), "{uid}")

    def read(self) -> List[ProviderRead]:
        """Retrieve all providers from the Federation-Registry."""
        self.logger.info("Looking for all Providers")
        self.logger.debug(f"Url={self.multi_url}")

        resp = requests.get(
            url=self.multi_url, headers=self.read_headers, timeout=TIMEOUT
        )
        if resp.status_code == status.HTTP_200_OK:
            self.logger.info("Retrieved")
            self.logger.debug(f"{resp.json()}")
            return [ProviderRead(**i) for i in resp.json()]

        self.logger.debug(f"Status code: {resp.status_code}")
        self.logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def create(self, *, data: ProviderCreateExtended) -> ProviderReadExtended:
        """Create new instance."""
        self.logger.info(f"Creating Provider={data.name}")
        self.logger.debug(f"Url={self.multi_url}")
        self.logger.debug(f"New Data={data}")

        resp = requests.post(
            url=self.multi_url,
            json=jsonable_encoder(data),
            headers=self.write_headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == status.HTTP_201_CREATED:
            self.logger.info(f"Provider={data.name} created")
            self.logger.debug(f"{resp.json()}")
            return ProviderReadExtended(**resp.json())
        elif resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            self.logger.error(f"Provider={data.name} has not been created.")
            self.logger.error(f"{resp.json()}")
            return None

        self.logger.debug(f"Status code: {resp.status_code}")
        self.logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def remove(self, *, item: ProviderRead) -> None:
        """Remove item."""
        self.logger.info(f"Removing Provider={item.name}.")
        self.logger.debug(f"Url={self.single_url.format(uid=item.uid)}")

        resp = requests.delete(
            url=self.single_url.format(uid=item.uid),
            headers=self.write_headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == status.HTTP_204_NO_CONTENT:
            self.logger.info(f"Provider={item.name} removed")
            return None

        self.logger.debug(f"Status code: {resp.status_code}")
        self.logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()

    def update(
        self, *, new_data: ProviderCreateExtended, old_data: ProviderRead
    ) -> Optional[ProviderReadExtended]:
        """Update existing instance."""
        self.logger.info(f"Updating Provider={new_data.name}.")
        self.logger.debug(f"Url={self.single_url.format(uid=old_data.uid)}")
        self.logger.debug(f"New Data={new_data}")

        resp = requests.put(
            url=self.single_url.format(uid=old_data.uid),
            json=jsonable_encoder(new_data),
            headers=self.write_headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == status.HTTP_200_OK:
            self.logger.info(f"Provider={new_data.name} updated")
            self.logger.debug(f"{resp.json()}")
            return ProviderReadExtended(**resp.json())
        elif resp.status_code == status.HTTP_304_NOT_MODIFIED:
            self.logger.info(
                f"New data match stored data. Provider={new_data.name} not modified"
            )
            return None
        elif resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            self.logger.error(f"Provider={new_data.name} has not been updated.")
            self.logger.error(f"{resp.json()}")
            return None

        self.logger.debug(f"Status code: {resp.status_code}")
        self.logger.debug(f"Message: {resp.text}")
        resp.raise_for_status()
