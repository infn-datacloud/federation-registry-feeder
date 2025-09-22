"""Core pydantic models."""

from typing import Annotated

from pydantic import BaseModel, Field


class BaseNode(BaseModel):
    """Common attributes and validators for a schema of a generic neo4j Node.

    Add description field and a validator converting UUIDs to str.

    Attributes:
    ----------
        description (str): Brief item description
    """

    description: Annotated[str, Field(default="", description="Brief item description")]
