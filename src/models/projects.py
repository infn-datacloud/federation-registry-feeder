"""Pydantic models of the Project owned by a Provider."""

from typing import Annotated

from pydantic import Field

from src.models.core import BaseNode


class Project(BaseNode):
    """Model with Project public attributes.

    Attributes:
    ----------
        description (str): Brief description.
        name (str): Project name in the Provider.
        uuid (str): Project unique ID in the Provider
    """

    name: Annotated[str, Field(description="Project name in the Provider.")]
    iaas_uuid: Annotated[str, Field(description="Project unique ID in the Provider.")]
