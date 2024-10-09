import copy
import os
from typing import Literal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fed_reg.provider.schemas_extended import (
    ProviderCreateExtended,
    ProviderRead,
    ProviderReadExtended,
)
from pytest_cases import case, parametrize, parametrize_with_cases
from requests.exceptions import ConnectionError, ReadTimeout

from src.fed_reg_conn import CRUD
from tests.fed_reg.utils import crud_dict, execute_operation, provider_dict
from tests.schemas.utils import random_lower_string


class CaseCRUDCreation:
    @parametrize(attr=["url", "read_headers", "write_headers", "logger", "settings"])
    def case_missing_attr(self, attr: str) -> str:
        return attr


class CaseReadProviders:
    def case_empty_list(self) -> list[ProviderRead]:
        return []

    def case_providers(self) -> list[ProviderRead]:
        return [ProviderRead(uid=uuid4(), **provider_dict())]


class CaseConnException:
    @parametrize(exception=[ConnectionError, ReadTimeout])
    def case_exception(
        self,
        exception: type[ConnectionError] | type[ReadTimeout],
    ) -> type[ConnectionError] | type[ReadTimeout]:
        return exception


class CaseRequest:
    def case_get(self) -> Literal["get"]:
        return "get"

    @case(tags="write")
    def case_put(self) -> Literal["put"]:
        return "put"

    @case(tags="write")
    def case_post(self) -> Literal["post"]:
        return "post"

    def case_delete(self) -> Literal["delete"]:
        return "delete"


class CaseErrorCode:
    @case(tags="unmanaged")
    @parametrize(
        code=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_408_REQUEST_TIMEOUT,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]
    )
    def case_unmanaged_error_code(self, code: int) -> int:
        return code

    @case(tags="managed")
    @parametrize(code=[status.HTTP_422_UNPROCESSABLE_ENTITY])
    def case_managed_error_code(self, code: int) -> int:
        return code


def test_crud_class() -> None:
    """Valid CRUD schema."""
    d = crud_dict()
    crud = CRUD(**d)
    assert crud.single_url == os.path.join(d.get("url"), "{uid}")
    assert crud.multi_url == d.get("url")
    assert crud.read_headers == d.get("read_headers")
    assert crud.write_headers == d.get("write_headers")
    assert crud.logger == d.get("logger")
    assert not crud.error
    assert crud.timeout == d.get("settings").FED_REG_TIMEOUT


@parametrize_with_cases("missing_attr", cases=CaseCRUDCreation)
def test_invalid_crud_class(missing_attr: str) -> None:
    """Invalid CRUD schema.

    Missing required attributes.
    """
    d = crud_dict()
    d.pop(missing_attr)
    with pytest.raises(TypeError):
        CRUD(**d)


@patch("src.fed_reg_conn.requests.get")
@parametrize_with_cases("providers", cases=CaseReadProviders)
def test_read(mock_get: Mock, providers: list[ProviderRead]) -> None:
    crud = CRUD(**crud_dict())
    mock_get.return_value.status_code = status.HTTP_200_OK
    mock_get.return_value.json.return_value = jsonable_encoder(providers)

    resp_body = crud.read()
    mock_get.return_value.raise_for_status.assert_not_called()
    assert len(providers) == len(resp_body)
    for provider in resp_body:
        assert isinstance(provider, ProviderRead)
    assert not crud.error


@patch("src.fed_reg_conn.requests.post")
def test_create(mock_post: Mock) -> None:
    crud = CRUD(**crud_dict())
    provider_create = ProviderCreateExtended(**provider_dict())
    provider_read_extended = ProviderReadExtended(uid=uuid4(), **provider_create.dict())
    mock_post.return_value.status_code = status.HTTP_201_CREATED
    mock_post.return_value.json.return_value = jsonable_encoder(provider_read_extended)

    resp_body = crud.create(data=provider_create)
    mock_post.return_value.raise_for_status.assert_not_called()
    assert isinstance(resp_body, ProviderReadExtended)
    assert not crud.error


@patch(
    "src.fed_reg_conn.requests.delete",
    return_value=Mock(status_code=status.HTTP_204_NO_CONTENT),
)
def test_remove(mock_delete: Mock) -> None:
    crud = CRUD(**crud_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_dict())

    resp_body = crud.remove(item=provider_read)
    mock_delete.return_value.raise_for_status.assert_not_called()
    assert not resp_body
    assert not crud.error


@patch("src.fed_reg_conn.requests.put")
def test_update(mock_put: Mock) -> None:
    crud = CRUD(**crud_dict())
    provider_create = ProviderCreateExtended(**provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())
    provider_create.name = random_lower_string()
    new_read_data = ProviderReadExtended(
        **provider_create.dict(), uid=provider_read.uid
    )
    mock_put.return_value.status_code = status.HTTP_200_OK
    mock_put.return_value.json.return_value = jsonable_encoder(new_read_data)

    resp_body = crud.update(new_data=provider_create, old_data=provider_read)
    mock_put.return_value.raise_for_status.assert_not_called()
    assert isinstance(resp_body, ProviderReadExtended)
    assert not crud.error


@patch(
    "src.fed_reg_conn.requests.put",
    return_value=Mock(status_code=status.HTTP_304_NOT_MODIFIED),
)
def test_update_no_changes(mock_put: Mock) -> None:
    crud = CRUD(**crud_dict())
    provider_create = ProviderCreateExtended(**provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())

    resp_body = crud.update(new_data=provider_create, old_data=provider_read)
    mock_put.return_value.raise_for_status.assert_not_called()
    assert not resp_body
    assert not crud.error


@parametrize_with_cases("error_code", cases=CaseErrorCode, has_tag="unmanaged")
@parametrize_with_cases("operation", cases=CaseRequest)
def test_generic_http_error(error_code: int, operation: str) -> None:
    """Endpoint responds with error codes."""
    crud = CRUD(**crud_dict())
    provider_create = ProviderCreateExtended(**provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())

    with patch(f"src.fed_reg_conn.requests.{operation}") as mock_req:
        mock_req.return_value.status_code = error_code
        execute_operation(
            crud=crud,
            operation=operation,
            provider_create=provider_create,
            provider_read=provider_read,
        )
        mock_req.return_value.raise_for_status.assert_called()
        assert crud.error


@parametrize_with_cases("error_code", cases=CaseErrorCode, has_tag="managed")
@parametrize_with_cases("operation", cases=CaseRequest, has_tag="write")
def test_managed_http_error(error_code: int, operation: str) -> None:
    """Endpoint responds with error codes."""
    crud = CRUD(**crud_dict())
    provider_create = ProviderCreateExtended(**provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())

    with patch(f"src.fed_reg_conn.requests.{operation}") as mock_req:
        mock_req.return_value.status_code = error_code
        if operation == "post":
            resp = crud.create(data=provider_create)
            assert not resp
        elif operation == "put":
            new_data = copy.deepcopy(provider_create)
            new_data.name = random_lower_string()
            resp = crud.update(new_data=new_data, old_data=provider_read)
            assert not resp
        mock_req.return_value.raise_for_status.assert_not_called()
        assert crud.error


@parametrize_with_cases("exception", cases=CaseConnException)
@parametrize_with_cases("operation", cases=CaseRequest)
def test_read_no_connection(
    operation: str, exception: type[ConnectionError] | type[ReadTimeout]
) -> None:
    """Connection error: no connection or read timeout.

    This error is not related to a status code.
    """
    crud = CRUD(**crud_dict())
    provider_create = ProviderCreateExtended(**provider_dict())
    provider_read = ProviderRead(uid=uuid4(), **provider_create.dict())

    with patch(f"src.fed_reg_conn.requests.{operation}") as mock_req:
        mock_req.side_effect = exception()
        with pytest.raises(exception):
            execute_operation(
                crud=crud,
                operation=operation,
                provider_create=provider_create,
                provider_read=provider_read,
            )
