import subprocess

from fedreg.v1.provider.schemas_extended import IdentityProviderCreate, find_duplicates
from fedreg.v1.sla.schemas import SLABase
from fedreg.v1.user_group.schemas import UserGroupBase
from liboidcagent import get_access_token_by_issuer_url
from pydantic import AnyHttpUrl, Field, validator

from src.models.config import get_settings


def retrieve_token(endpoint: str, *, audience: str | None = None):
    """Retrieve token using OIDC-Agent.

    If the container name is set use perform a docker exec command, otherwise use a
    local instance."""
    settings = get_settings()
    min_valid_period = 5 * 60  # 5 min

    if settings.OIDC_AGENT_CONTAINER_NAME is not None:
        token_cmd = subprocess.run(
            [
                "docker",
                "exec",
                settings.OIDC_AGENT_CONTAINER_NAME,
                "oidc-token",
                f"--time={min_valid_period}",
                f"--aud={audience}",
                endpoint,
            ],
            capture_output=True,
            text=True,
        )
        if token_cmd.returncode > 0:
            raise ValueError(token_cmd.stderr if token_cmd.stderr else token_cmd.stdout)
        token = token_cmd.stdout.strip("\n")
        return token

    token = get_access_token_by_issuer_url(
        endpoint, min_valid_period=min_valid_period, audience=audience
    )
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

    @validator("user_groups")
    @classmethod
    def validate_user_groups(cls, v: list[UserGroup]) -> list[UserGroup]:
        """Verify the list is not empty and there are no duplicates."""
        find_duplicates(v, "name")
        assert len(v), "Identity provider's user group list can't be empty"
        return v

    @validator("token", pre=True, always=True)
    @classmethod
    def get_token(cls, v: str, values) -> str:
        if v == "":
            return retrieve_token(values.get("endpoint"))
        return v
