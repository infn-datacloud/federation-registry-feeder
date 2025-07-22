import urllib.parse
from typing import Any

import requests
from fedreg.provider.schemas_extended import IdentityProviderCreate, find_duplicates
from fedreg.sla.schemas import SLABase
from fedreg.user_group.schemas import UserGroupBase
from pydantic import AnyHttpUrl, Field, root_validator, validator


def retrieve_token(*, endpoint: str, client_id: str, client_secret: str):
    """Retrieve token using client_id and secret.

    Query the instrospection endpoint to retrieve the token endpoint. Ask a new token.
    """
    resp = requests.get(
        urllib.parse.urljoin(endpoint, ".well-known/openid-configuration")
    )
    if resp.status_code != 200:
        raise ValueError("Failed to contact introspection endpoint")
    token_url = resp.json().get("token_endpoint")
    resp = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if resp.status_code != 200:
        raise ValueError("Failed to retrieve token")
    token = resp.json().get("access_token")
    return token


class SLA(SLABase):
    projects: list[str] = Field(
        default_factory=list, description="list of projects UUID"
    )

    @validator("projects")
    @classmethod
    def validate_projects(cls, v: list[str]) -> list[str]:
        find_duplicates(v)
        return v


class UserGroup(UserGroupBase):
    slas: list[SLA] = Field(description="list of SLAs")

    @validator("slas")
    @classmethod
    def validate_slas(cls, v: list[SLA]) -> list[SLA]:
        find_duplicates(v, "doc_uuid")
        return v


class Issuer(IdentityProviderCreate):
    endpoint: AnyHttpUrl = Field(description="issuer url", alias="issuer")
    token: str = Field(default="", description="Access token")
    user_groups: list[UserGroup] = Field(description="User groups")
    client_id: str = Field(
        description="ID of the client to contact to retrieve the access token"
    )
    client_secret: str = Field(
        description="Secret of the client to contact to retrieve the access token"
    )

    @validator("user_groups")
    @classmethod
    def validate_user_groups(cls, v: list[UserGroup]) -> list[UserGroup]:
        """Verify the list is not empty and there are no duplicates."""
        find_duplicates(v, "name")
        assert len(v), "Identity provider's user group list can't be empty"
        return v

    @root_validator()
    @classmethod
    def set_token(cls, values: dict[str, Any]) -> str:
        token = values.get("token")
        if token == "":
            values["token"] = retrieve_token(
                endpoint=values.get("endpoint"),
                client_id=values.get("client_id"),
                client_secret=values.get("client_secret"),
            )
        return values
