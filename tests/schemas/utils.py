import ipaddress
import string
import time
from datetime import date
from random import choice, choices, randint
from typing import Tuple, Union

from pycountry import countries


def random_country() -> str:
    """Return random country."""
    return choice([i.name for i in countries])


def random_date() -> date:
    """Return a random date."""
    d = randint(1, int(time.time()))
    return date.fromtimestamp(d)


def random_ip(version: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    if version == "v4":
        return ipaddress.IPv4Address(randint(0, 2**32 - 1))
    elif version == "v6":
        return ipaddress.IPv6Address(randint(0, 2**128 - 1))


def random_lower_string() -> str:
    """Return a generic random string."""
    return "".join(choices(string.ascii_lowercase, k=32))


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
