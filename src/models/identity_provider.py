import subprocess
from typing import List, Optional

from app.auth_method.schemas import AuthMethodBase
from app.identity_provider.schemas import IdentityProviderBase
from app.provider.schemas_extended import find_duplicates
from app.sla.schemas import SLABase
from app.user_group.schemas import UserGroupBase
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


class Issuer(IdentityProviderBase):
    endpoint: AnyHttpUrl = Field(description="issuer url", alias="issuer")
    token: Optional[str] = Field(description="Access token")
    user_groups: List[UserGroup] = Field(description="User groups")
    relationship: Optional[AuthMethodBase] = Field(default=None, description="")

    @validator("user_groups")
    @classmethod
    def not_empty_list(cls, v: Optional[List[UserGroup]]) -> List[UserGroup]:
        if not v or len(v) == 0:
            raise ValueError("At least one user group must be specified.")
        return v

    @validator("token", pre=True, always=True)
    @classmethod
    def get_token(cls, v, values):
        # Generate token
        if not v:
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
        return v
