from random import choice
from typing import List, Optional


def random_image_status(*, exclude: Optional[List[str]] = None) -> str:
    """Return one of the possible image status types."""
    if exclude is None:
        exclude = []
    choices = set(
        [
            "queued",
            "saving",
            "uploading",
            "importing",
            "active",
            "deactivated",
            "killed",
            "deleted",
            "pending_delete",
        ]
    ) - set(exclude)
    return choice(list(choices))


def random_image_visibility(*, exclude: Optional[List[str]] = None) -> str:
    """Return one of the possible image visibility types."""
    if exclude is None:
        exclude = []
    choices = set(["public", "private", "shared", "community"]) - set(exclude)
    return choice(list(choices))


def random_network_status(*, exclude: Optional[List[str]] = None) -> str:
    """Return one of the possible network status types."""
    if exclude is None:
        exclude = []
    choices = set(["active", "build", "down", "error"]) - set(exclude)
    return choice(list(choices))
