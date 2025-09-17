from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils import invalid_empty


class Settings(BaseSettings):
    BLOCK_STORAGE_VOL_LABELS: Annotated[
        list[str],
        Field(default_factory=list, description="List of accepted volume type labels."),
    ]
    PROVIDERS_CONF_DIR: Annotated[
        Path,
        Field(
            default="providers-conf",
            description="Path to the directory containing the federated provider yaml "
            "configurations.",
        ),
    ]
    OIDC_AGENT_CONTAINER_NAME: Annotated[
        str | None,
        Field(
            default=None,
            description="Name of the container with the oidc-agent service instance.",
        ),
        AfterValidator(invalid_empty),
    ]
    FED_MGR_ENABLE: Annotated[
        bool, Field(default=False, description="Enable communication with Fed-Mgr")
    ]
    FED_MGR_URL: Annotated[
        AnyHttpUrl,
        Field(
            default="http://localhost:8000/api/v1",
            description="Federation-Manager base URL.",
        ),
    ]
    KAFKA_ENABLE: Annotated[
        bool, Field(default=False, description="Enable Kafka message exchange")
    ]
    KAFKA_BOOTSTRAP_SERVERS: Annotated[
        str,
        Field(
            default="localhost:9092",
            description="Kafka server hostnames. DNS name and port. "
            "Can be comma separeted list",
        ),
    ]
    KAFKA_TOPIC: Annotated[
        str,
        Field(
            default="federation-registry-feeder",
            description="Kafka topic to upload data",
        ),
    ]
    KAFKA_MAX_REQUEST_SIZE: Annotated[
        int,
        Field(
            default=104857600,
            description="Maximum size of a request to send to kafka (B).",
        ),
    ]
    KAFKA_CLIENT_NAME: Annotated[
        str,
        Field(
            default="fedreg-feeder",
            description="Client name to use when connecting to kafka",
        ),
    ]
    KAFKA_SSL_ENABLE: Annotated[
        bool, Field(default=False, description="Enable SSL connection with kafka")
    ]
    KAFKA_SSL_CACERT_PATH: Annotated[
        str | None, Field(default=None, descrption="Path to the SSL CA cert file")
    ]
    KAFKA_SSL_CERT_PATH: Annotated[
        str | None, Field(default=None, descrption="Path to the SSL cert file")
    ]
    KAFKA_SSL_KEY_PATH: Annotated[
        str | None, Field(default=None, descrption="Path to the SSL Key file")
    ]
    KAFKA_SSL_PASSWORD: Annotated[
        str | None, Field(default=None, descrption="SSL password")
    ]
    KAFKA_ALLOW_AUTO_CREATE_TOPICS: Annotated[
        bool,
        Field(
            default=False,
            description="Enable automatic creation of new topics if not yet in kafka",
        ),
    ]
    KAFKA_MSG_VERSION: Annotated[
        str,
        Field(
            default="1.2.0",
            description="Message version. It defines the fields in the message sent to "
            "kafka",
        ),
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached settings.

    Returns:
        Settings: Cached settings value.

    """
    return Settings()
