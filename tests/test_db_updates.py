import logging
from unittest.mock import Mock, patch

import pytest
from fed_reg.provider.schemas_extended import ProviderCreateExtended, ProviderRead
from requests import HTTPError

from src.config import URLs
from src.utils import update_database
from tests.schemas.utils import random_lower_string


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_do_nothing_to_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
) -> None:
    """No entries in the database and no new providers to add."""
    mock_crud_read.return_value = []
    update_database(
        service_api_url=service_endpoints,
        items=[],
        token=random_lower_string(),
        logger=logging.getLogger(),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_add_provider_to_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_create: ProviderCreateExtended,
) -> None:
    """No entries in the database and a new providers to add."""
    mock_crud_read.return_value = []
    update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=logging.getLogger(),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_called_once()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_delete_provider_from_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_read: ProviderRead,
) -> None:
    """One entry in the database and no tracked providers."""
    mock_crud_read.return_value = [provider_read]
    update_database(
        service_api_url=service_endpoints,
        items=[],
        token=random_lower_string(),
        logger=logging.getLogger(),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_called_once()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_update_provider_in_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderRead,
) -> None:
    mock_crud_read.return_value = [provider_read]
    update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=logging.getLogger(),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_called_once()
    mock_crud_remove.assert_not_called()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_read_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_create: ProviderCreateExtended,
) -> None:
    mock_crud_read.side_effect = HTTPError
    with pytest.raises(HTTPError):
        update_database(
            service_api_url=service_endpoints,
            items=[provider_create],
            token=random_lower_string(),
            logger=logging.getLogger(),
        )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_create_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_create: ProviderCreateExtended,
) -> None:
    mock_crud_read.return_value = []
    mock_crud_create.side_effect = HTTPError
    with pytest.raises(HTTPError):
        update_database(
            service_api_url=service_endpoints,
            items=[provider_create],
            token=random_lower_string(),
            logger=logging.getLogger(),
        )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_called_once()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_delete_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_read: ProviderRead,
) -> None:
    mock_crud_read.return_value = [provider_read]
    mock_crud_remove.side_effect = HTTPError
    with pytest.raises(HTTPError):
        update_database(
            service_api_url=service_endpoints,
            items=[],
            token=random_lower_string(),
            logger=logging.getLogger(),
        )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_called_once()


@patch("src.utils.CRUD.remove")
@patch("src.utils.CRUD.update")
@patch("src.utils.CRUD.create")
@patch("src.utils.CRUD.read")
def test_update_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    service_endpoints: URLs,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderRead,
) -> None:
    mock_crud_read.return_value = [provider_read]
    mock_crud_update.side_effect = HTTPError
    with pytest.raises(HTTPError):
        update_database(
            service_api_url=service_endpoints,
            items=[provider_create],
            token=random_lower_string(),
            logger=logging.getLogger(),
        )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_called_once()
    mock_crud_remove.assert_not_called()
