import string
import time
from datetime import date
from ipaddress import IPv4Address, IPv6Address
from random import choices, randint, random

from pydantic import AnyHttpUrl


def random_date() -> date:
    """Return a random date."""
    d = randint(1, int(time.time()))
    return date.fromtimestamp(d)


def random_float(start: int, end: int) -> float:
    """Return a random float between start and end (included)."""
    return randint(start, end - 1) + random()


def random_ip(version: str = "v4") -> IPv4Address | IPv6Address:
    if version == "v4":
        return IPv4Address(randint(0, 2**32 - 1))
    elif version == "v6":
        return IPv6Address(randint(0, 2**128 - 1))


def random_lower_string() -> str:
    """Return a generic random string."""
    return "".join(choices(string.ascii_lowercase, k=32))


def random_url() -> AnyHttpUrl:
    """Return a random URL."""
    return "https://" + random_lower_string() + ".com"
