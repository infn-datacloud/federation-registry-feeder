import os
from logging import getLogger
from typing import Any

from fed_reg.provider.schemas_extended import ProviderCreateExtended, ProviderRead

from src.crud import CRUD
from src.models.config import APIVersions, Settings, URLs
from tests.schemas.utils import random_lower_string, random_provider_type, random_url


def crud_dict() -> dict[str, Any]:
    """Dict with CRUD minimal attributes.

    The CRUD object is used to interact with the federation-registry API.
    """
    read_header = {"authorization": f"Bearer {random_lower_string()}"}
    write_header = {
        **read_header,
        "accept": "application/json",
        "content-type": "application/json",
    }
    logger = getLogger("test")
    settings = Settings(api_ver=APIVersions())
    return {
        "url": random_url(),
        "read_headers": read_header,
        "write_headers": write_header,
        "logger": logger,
        "settings": settings,
    }


def execute_operation(
    *,
    crud: CRUD,
    operation: str,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderRead,
) -> None:
    if operation == "get":
        crud.read()
    elif operation == "post":
        crud.create(data=provider_create)
    elif operation == "delete":
        crud.remove(item=provider_read)
    elif operation == "put":
        provider_create.name = random_lower_string()
        crud.update(new_data=provider_create, old_data=provider_read)


def provider_dict() -> dict[str, Any]:
    return {"name": random_lower_string(), "type": random_provider_type()}


def service_endpoints_dict() -> dict[str, Any]:
    return {k: os.path.join(random_url(), k) for k in URLs.__fields__.keys()}
