import ipaddress
import string
import time
from datetime import date
from random import choice, choices, randint, random
from typing import List, Optional, Tuple, Union

from fed_reg.image.enum import ImageOS
from fed_reg.provider.enum import ProviderType
from fed_reg.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
)
from pycountry import countries
from pydantic import AnyHttpUrl


def random_block_storage_service_name() -> str:
    """Return one of the possible BlockStorageService names."""
    return choice([i.value for i in BlockStorageServiceName])


def random_country() -> str:
    """Return random country."""
    return choice([i.name for i in countries])


def random_compute_service_name() -> str:
    """Return one of the possible ComputeService names."""
    return choice([i.value for i in ComputeServiceName])


def random_date() -> date:
    """Return a random date."""
    d = randint(1, int(time.time()))
    return date.fromtimestamp(d)


def random_float(start: int, end: int) -> float:
    """Return a random float between start and end (included)."""
    return randint(start, end - 1) + random()


def random_identity_service_name() -> str:
    """Return one of the possible IdentityService names."""
    return choice([i.value for i in IdentityServiceName])


def random_image_os_type() -> str:
    """Return one of the possible image OS values."""
    return choice([i.value for i in ImageOS])


def random_ip(
    version: str = "v4",
) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    if version == "v4":
        return ipaddress.IPv4Address(randint(0, 2**32 - 1))
    elif version == "v6":
        return ipaddress.IPv6Address(randint(0, 2**128 - 1))


def random_lower_string() -> str:
    """Return a generic random string."""
    return "".join(choices(string.ascii_lowercase, k=32))


def random_network_service_name() -> str:
    """Return one of the possible NetworkService names."""
    return choice([i.value for i in NetworkServiceName])


def random_provider_type(*, exclude: Optional[List[str]] = None) -> str:
    """Return one of the possible provider types."""
    if exclude is None:
        exclude = []
    choices = set([i for i in ProviderType]) - set(exclude)
    return choice(list(choices))


def random_start_end_dates() -> Tuple[date, date]:
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


def random_url() -> AnyHttpUrl:
    """Return a random URL."""
    return "https://" + random_lower_string() + ".com"
