import os
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.provider.schemas_extended import ProviderCreateExtended, ProviderReadExtended
from fastapi.encoders import jsonable_encoder

from src.config import URLs
from src.utils import update_database
from tests.schemas.utils import random_lower_string, random_provider_type, random_url


@pytest.fixture
def provider_urls() -> URLs:
    base_url = random_url()
    return URLs(**{k: os.path.join(base_url, k) for k in URLs.__fields__.keys()})


@patch("src.crud.requests.get")
def test_do_nothing_to_db(mock_get: Mock, provider_urls: URLs) -> None:
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([])
    update_database(
        service_api_url=provider_urls, items=[], token=random_lower_string()
    )


@patch("src.crud.requests.post")
@patch("src.crud.requests.get")
def test_add_provider_to_db(
    mock_get: Mock, mock_post: Mock, provider_urls: URLs
) -> None:
    new_provider = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    created_provider = ProviderReadExtended(uid=uuid4(), **new_provider.dict())
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([])
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = jsonable_encoder(created_provider)
    update_database(
        service_api_url=provider_urls, items=[new_provider], token=random_lower_string()
    )


@patch("src.crud.requests.delete")
@patch("src.crud.requests.get")
def test_delete_provider_from_db(
    mock_get: Mock, mock_del: Mock, provider_urls: URLs
) -> None:
    provider = ProviderReadExtended(
        uid=uuid4(),
        name=random_lower_string(),
        type=random_provider_type(),
        identity_providers=[],
        projects=[],
        regions=[],
    )
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([provider])
    mock_del.return_value.status_code = 204
    update_database(
        service_api_url=provider_urls, items=[], token=random_lower_string()
    )


@patch("src.crud.requests.put")
@patch("src.crud.requests.get")
def test_update_provider_in_db(
    mock_get: Mock, mock_put: Mock, provider_urls: URLs
) -> None:
    old_provider = ProviderReadExtended(
        uid=uuid4(),
        name=random_lower_string(),
        type=random_provider_type(),
        identity_providers=[],
        projects=[],
        regions=[],
    )
    new_provider = ProviderCreateExtended(
        name=old_provider.name, type=old_provider.type
    )
    updated_provider = ProviderReadExtended(uid=old_provider.uid, **new_provider.dict())
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder([old_provider])
    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = jsonable_encoder([updated_provider])
    update_database(
        service_api_url=provider_urls, items=[new_provider], token=random_lower_string()
    )
