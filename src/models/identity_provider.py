import subprocess
from typing import List

from fed_reg.provider.schemas_extended import IdentityProviderCreate, find_duplicates
from fed_reg.sla.schemas import SLABase
from fed_reg.user_group.schemas import UserGroupBase
from pydantic import AnyHttpUrl, Field, validator

from src.config import get_settings


class SLA(SLABase):
    projects: List[str] = Field(
        default_factory=list, description="List of projects UUID"
    )

    @validator("projects")
    @classmethod
    def validate_projects(cls, v: List[str]) -> List[str]:
        find_duplicates(v)
        return v


class UserGroup(UserGroupBase):
    slas: List[SLA] = Field(description="List of SLAs")

    @validator("slas")
    @classmethod
    def validate_slas(cls, v: List[SLA]) -> List[SLA]:
        find_duplicates(v, "doc_uuid")
        return v


class Issuer(IdentityProviderCreate):
    endpoint: AnyHttpUrl = Field(description="issuer url", alias="issuer")
    token: str = Field(default="", description="Access token")
    user_groups: List[UserGroup] = Field(description="User groups")

    @validator("user_groups")
    @classmethod
    def validate_user_groups(cls, v: List[UserGroup]) -> List[UserGroup]:
        """Verify the list is not empty and there are no duplicates."""
        find_duplicates(v, "name")
        assert len(v), "Identity provider's user group list can't be empty"
        return v

    @validator("token", pre=True, always=True)
    @classmethod
    def get_token(cls, v: str, values) -> str:
        # Generate token
        if v == "":
            settings = get_settings()
            token_cmd = subprocess.run(
                [
                    "docker",
                    "exec",
                    settings.OIDC_AGENT_CONTAINER_NAME,
                    "oidc-token",
                    values.get("endpoint"),
                ],
                capture_output=True,
                text=True,
            )
            if token_cmd.returncode > 0:
                raise ValueError(
                    token_cmd.stderr if token_cmd.stderr else token_cmd.stdout
                )
            return token_cmd.stdout.strip("\n")
        return v
