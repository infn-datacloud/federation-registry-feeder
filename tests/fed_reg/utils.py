import os
from datetime import date
from logging import getLogger
from random import choice
from typing import Any

from fed_reg.image.enum import ImageOS
from fed_reg.provider.enum import ProviderType
from fed_reg.provider.schemas_extended import ProviderCreateExtended, ProviderRead
from fed_reg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
    ObjectStoreServiceName,
)
from pycountry import countries

from src.fed_reg_conn import CRUD
from src.models.config import APIVersions, Settings, URLs
from tests.utils import random_date, random_lower_string, random_url


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


def service_endpoints_dict() -> dict[str, Any]:
    return {k: os.path.join(random_url(), k) for k in URLs.__fields__.keys()}


# Fed-Reg classes specific


def random_country() -> str:
    """Return random country."""
    return choice([i.name for i in countries])


def random_block_storage_service_name() -> str:
    """Return one of the possible BlockStorageService names."""
    return choice([i.value for i in BlockStorageServiceName])


def random_compute_service_name() -> str:
    """Return one of the possible ComputeService names."""
    return choice([i.value for i in ComputeServiceName])


def random_identity_service_name() -> str:
    """Return one of the possible IdentityService names."""
    return choice([i.value for i in IdentityServiceName])


def random_network_service_name() -> str:
    """Return one of the possible NetworkService names."""
    return choice([i.value for i in NetworkServiceName])


def random_object_store_service_name() -> str:
    """Return one of the possible NetworkService names."""
    return choice([i.value for i in ObjectStoreServiceName])


def random_image_os_type() -> str:
    """Return one of the possible image OS values."""
    return choice([i.value for i in ImageOS])


def random_provider_type(*, exclude: list[str] | None = None) -> str:
    """Return one of the possible provider types."""
    if exclude is None:
        exclude = []
    choices = set([i for i in ProviderType]) - set(exclude)
    return choice(list(choices))


def random_start_end_dates() -> tuple[date, date]:
    """Return a random couples of valid start and end dates (in order)."""
    d1 = random_date()
    d2 = random_date()
    while d1 == d2:
        d2 = random_date()
    if d1 < d2:
        start_date = d1
        end_date = d2
    else:
        start_date = d2
        end_date = d1
    return start_date, end_date


def fed_reg_provider_dict() -> dict[str, Any]:
    return {"name": random_lower_string(), "type": random_provider_type()}
