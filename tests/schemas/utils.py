import string
import time
from datetime import date
from random import choices, randint
from typing import Tuple


def random_date() -> date:
    """Return a random date."""
    d = randint(1, int(time.time()))
    return date.fromtimestamp(d)


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
