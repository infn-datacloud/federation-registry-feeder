from logging import getLogger
from unittest.mock import Mock, patch
from uuid import uuid4

from fedreg.provider.schemas_extended import ProviderCreateExtended, ProviderRead
from pytest_cases import parametrize_with_cases
from requests.exceptions import ConnectionError, HTTPError

from src.fed_reg_conn import get_read_write_headers, update_database
from src.models.config import APIVersions, Settings, URLs
from tests.fed_reg.utils import fedreg_provider_dict, service_endpoints_dict
from tests.utils import random_lower_string


class CaseErrors:
    def case_conn_error(self) -> ConnectionError:
        return ConnectionError()

    def case_http_error(self) -> HTTPError:
        return HTTPError()


def test_headers_creation() -> None:
    token = "test"
    (read, write) = get_read_write_headers(token=token)
    assert read
    assert write
    assert "authorization" in read.keys()
    assert read["authorization"] == f"Bearer {token}"
    assert "authorization" in write.keys()
    assert write["authorization"] == f"Bearer {token}"
    assert write["content-type"] == "application/json"


@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_do_nothing_to_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
) -> None:
    """No entries in the database and no new providers to add."""
    service_endpoints = URLs(**service_endpoints_dict())
    mock_crud_read.return_value = []

    assert update_database(
        service_api_url=service_endpoints,
        items=[],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_add_provider_to_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
) -> None:
    """No entries in the database and a new providers to add."""
    service_endpoints = URLs(**service_endpoints_dict())
    provider_create = ProviderCreateExtended(**fedreg_provider_dict())
    mock_crud_read.return_value = []

    assert update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_called_once()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_delete_provider_from_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
) -> None:
    """One entry in the database and no tracked providers."""
    service_endpoints = URLs(**service_endpoints_dict())
    provider_read = ProviderRead(uid=uuid4(), **fedreg_provider_dict())
    mock_crud_read.return_value = [provider_read]

    assert update_database(
        service_api_url=service_endpoints,
        items=[],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_called_once()


@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_update_provider_in_db(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
) -> None:
    service_endpoints = URLs(**service_endpoints_dict())
    provider_create = ProviderCreateExtended(**fedreg_provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())
    mock_crud_read.return_value = [provider_read]

    assert update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_called_once()
    mock_crud_remove.assert_not_called()


@parametrize_with_cases("error", cases=CaseErrors)
@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_read_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    error: ConnectionError | HTTPError,
) -> None:
    service_endpoints = URLs(**service_endpoints_dict())
    provider_create = ProviderCreateExtended(**fedreg_provider_dict())
    mock_crud_read.side_effect = error

    assert not update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@parametrize_with_cases("error", cases=CaseErrors)
@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_create_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    error: ConnectionError | HTTPError,
) -> None:
    service_endpoints = URLs(**service_endpoints_dict())
    provider_create = ProviderCreateExtended(**fedreg_provider_dict())
    mock_crud_read.return_value = []
    mock_crud_create.side_effect = error

    assert not update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_called_once()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()


@parametrize_with_cases("error", cases=CaseErrors)
@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_delete_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    error: ConnectionError | HTTPError,
) -> None:
    service_endpoints = URLs(**service_endpoints_dict())
    provider_read = ProviderRead(uid=uuid4(), **fedreg_provider_dict())
    mock_crud_read.return_value = [provider_read]
    mock_crud_remove.side_effect = error

    assert not update_database(
        service_api_url=service_endpoints,
        items=[],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_called_once()


@parametrize_with_cases("error", cases=CaseErrors)
@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_update_error(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
    error: ConnectionError | HTTPError,
) -> None:
    service_endpoints = URLs(**service_endpoints_dict())
    provider_create = ProviderCreateExtended(**fedreg_provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())
    mock_crud_read.return_value = [provider_read]
    mock_crud_update.side_effect = error

    assert not update_database(
        service_api_url=service_endpoints,
        items=[provider_create],
        token=random_lower_string(),
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_called_once()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_called_once()
    mock_crud_remove.assert_not_called()


@patch("src.fed_reg_conn.CRUD.remove")
@patch("src.fed_reg_conn.CRUD.update")
@patch("src.fed_reg_conn.CRUD.create")
@patch("src.fed_reg_conn.CRUD.read")
def test_no_token(
    mock_crud_read: Mock,
    mock_crud_create: Mock,
    mock_crud_update: Mock,
    mock_crud_remove: Mock,
) -> None:
    service_endpoints = URLs(**service_endpoints_dict())
    assert not update_database(
        service_api_url=service_endpoints,
        items=[],
        token="",
        logger=getLogger("test"),
        settings=Settings(api_ver=APIVersions()),
    )
    mock_crud_read.assert_not_called()
    mock_crud_create.assert_not_called()
    mock_crud_update.assert_not_called()
    mock_crud_remove.assert_not_called()
