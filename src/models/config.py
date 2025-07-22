from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel, BaseSettings, Field, validator


class URLs(BaseModel):
    flavors: AnyHttpUrl = Field(description="Flavors endpoint")
    identity_providers: AnyHttpUrl = Field(description="Identity Providers endpoint")
    images: AnyHttpUrl = Field(description="Images endpoint")
    locations: AnyHttpUrl = Field(description="Locations endpoint")
    networks: AnyHttpUrl = Field(description="Networks endpoint")
    projects: AnyHttpUrl = Field(description="Projects endpoint")
    providers: AnyHttpUrl = Field(description="Providers endpoint")
    block_storage_quotas: AnyHttpUrl = Field(
        description="Block Storage Quotas endpoint"
    )
    compute_quotas: AnyHttpUrl = Field(description="Compute Quotas endpoint")
    network_quotas: AnyHttpUrl = Field(description="Network Quotas endpoint")
    object_store_quotas: AnyHttpUrl = Field(description="ObjectStore Quotas endpoint")
    regions: AnyHttpUrl = Field(description="Regions endpoint")
    block_storage_services: AnyHttpUrl = Field(
        description="Block Storage Services endpoint"
    )
    compute_services: AnyHttpUrl = Field(description="Compute Services endpoint")
    identity_services: AnyHttpUrl = Field(description="Identity Services endpoint")
    network_services: AnyHttpUrl = Field(description="Network Services endpoint")
    slas: AnyHttpUrl = Field(description="SLAs endpoint")
    user_groups: AnyHttpUrl = Field(description="User Groups endpoint")


class APIVersions(BaseSettings):
    FLAVORS: str = Field(default="v1", description="Flavors API version to use")
    IDENTITY_PROVIDERS: str = Field(
        default="v1", description="Identity providers API version to use"
    )
    IMAGES: str = Field(default="v1", description="Images API version to use")
    LOCATIONS: str = Field(default="v1", description="Locations API version to use")
    NETWORKS: str = Field(default="v1", description="Networks API version to use")
    PROJECTS: str = Field(default="v1", description="Projects API version to use")
    PROVIDERS: str = Field(default="v1", description="Providers API version to use")
    BLOCK_STORAGE_QUOTAS: str = Field(
        default="v1", description="Block Storage Quotas API version to use"
    )
    COMPUTE_QUOTAS: str = Field(
        default="v1", description="Compute Quotas API version to use"
    )
    NETWORK_QUOTAS: str = Field(
        default="v1", description="Network Quotas API version to use"
    )
    OBJECT_STORE_QUOTAS: str = Field(
        default="v1", description="Object Store Quotas API version to use"
    )
    REGIONS: str = Field(default="v1", description="Regions API version to use")
    BLOCK_STORAGE_SERVICES: str = Field(
        default="v1", description="Block Storage Services API version to use"
    )
    COMPUTE_SERVICES: str = Field(
        default="v1", description="Compute Services API version to use"
    )
    IDENTITY_SERVICES: str = Field(
        default="v1", description="Identity Services API version to use"
    )
    NETWORK_SERVICES: str = Field(
        default="v1", description="Network Services API version to use"
    )
    SLAS: str = Field(default="v1", description="SLAs API version to use")
    USER_GROUPS: str = Field(default="v1", description="User groups API version to use")

    class Config:
        """Sub class to set attribute as case sensitive."""

        case_sensitive = True


class Settings(BaseSettings):
    FED_REG_API_URL: AnyHttpUrl = Field(
        default="http://localhost:8000/api", description="Federation-Registry base URL"
    )
    FED_REG_TIMEOUT: int = Field(
        default=30,
        description="Timeout [s] for the HTTP requests made to the Federation-Registry",
    )
    BLOCK_STORAGE_VOL_LABELS: list[str] = Field(
        default_factory=list, description="List of accepted volume type labels."
    )
    PROVIDERS_CONF_DIR: Path = Field(
        default="providers-conf",
        description="Path to the directory containing the federated provider \
            yaml configurations.",
    )
    KAFKA_ENABLE: bool = Field(
        default=False, description="Enable Kafka message exchange"
    )
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        description="Kafka server hostnames. DNS name and port. Can be comma separeted "
        "list",
    )
    KAFKA_TOPIC: str = Field(
        default="federation-registry-feeder", description="Kafka topic to upload data"
    )
    KAFKA_MAX_REQUEST_SIZE: int = Field(
        default=104857600, description="Maximum size of a request to send to kafka (B)."
    )
    KAFKA_CLIENT_NAME: str = Field(
        default="fedreg-feeder",
        description="Client name to use when connecting to kafka",
    )
    KAFKA_SSL_ENABLE: bool = Field(
        default=False, description="Enable SSL connection with kafka"
    )
    KAFKA_SSL_CACERT_PATH: str | None = Field(
        default=None, descrption="Path to the SSL CA cert file"
    )
    KAFKA_SSL_CERT_PATH: str | None = Field(
        default=None, descrption="Path to the SSL cert file"
    )
    KAFKA_SSL_KEY_PATH: str | None = Field(
        default=None, descrption="Path to the SSL Key file"
    )
    KAFKA_SSL_PASSWORD: str | None = Field(default=None, descrption="SSL password")
    KAFKA_ALLOW_AUTO_CREATE_TOPICS: bool = Field(
        default=False,
        description="Enable automatic creation of new topics if not yet in kafka",
    )
    KAFKA_MSG_VERSION: str = Field(
        default="1.2.0",
        description="Message version. It defines the fields in the message sent to "
        "kafka",
    )

    api_ver: APIVersions = Field(description="API versions.")

    @validator("PROVIDERS_CONF_DIR")
    @classmethod
    def convert_path_to_str(cls, v: Path) -> str:
        return str(v)

    class Config:
        """Sub class to set attribute as case sensitive."""

        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached settings."""
    return Settings(api_ver=APIVersions())
