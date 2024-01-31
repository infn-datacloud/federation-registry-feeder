from typing import Type, Union
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.provider.schemas_extended import (
    ProviderCreateExtended,
    ProviderRead,
    ProviderReadExtended,
)
from fastapi import status
from fastapi.encoders import jsonable_encoder
from pytest_cases import parametrize, parametrize_with_cases
from requests.exceptions import ConnectionError, ReadTimeout

from src.crud import CRUD
from src.utils import get_read_write_headers
from tests.schemas.utils import random_lower_string, random_provider_type, random_url


class CaseConnException:
    @parametrize(exception=[ConnectionError, ReadTimeout])
    def case_exception(
        self,
        exception: Union[Type[ConnectionError], Type[ReadTimeout]],
    ) -> Union[Type[ConnectionError], Type[ReadTimeout]]:
        return exception


class CaseRequest:
    @parametrize(operation=["get", "put", "post", "delete"])
    def case_operation(self, operation: str) -> str:
        return operation


class CaseErrorCode:
    @parametrize(
        code=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_408_REQUEST_TIMEOUT,
            status.HTTP_409_CONFLICT,
            status.HTTP_410_GONE,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]
    )
    def case_error_code(self, code: int) -> int:
        return code


class CaseCRUDCreation:
    @parametrize(attr=["url", "read_headers", "write_headers"])
    def case_missing_attr(self, attr: str) -> str:
        return attr


def execute_request(*, crud: CRUD, request: str) -> None:
    if request == "get":
        crud.read()
    elif request == "post":
        data = ProviderCreateExtended(
            name=random_lower_string(), type=random_provider_type()
        )
        crud.create(data=data)
    elif request == "delete":
        item = ProviderRead(
            uid=uuid4(), name=random_lower_string(), type=random_provider_type()
        )
        crud.remove(item=item)
    elif request == "put":
        old_data = ProviderCreateExtended(
            name=random_lower_string(), type=random_provider_type()
        )
        item = ProviderReadExtended(uid=uuid4(), **old_data.dict())
        new_data = ProviderCreateExtended(
            name=random_lower_string(), type=random_provider_type()
        )
        crud.update(new_data=new_data, old_data=item)


def test_crud_class() -> None:
    read_header, write_header = get_read_write_headers(token=random_lower_string())
    CRUD(url=random_url(), read_headers=read_header, write_headers=write_header)


@parametrize_with_cases("missing_attr", cases=CaseCRUDCreation)
def test_invalid_crud_class(missing_attr: str) -> None:
    url = None if missing_attr == "url" else random_url()
    read_header, write_header = get_read_write_headers(token=random_lower_string())
    if missing_attr == "read_headers":
        read_header = None
    if missing_attr == "write_headers":
        write_header = None
    with pytest.raises(ValueError):
        CRUD(url=url, read_headers=read_header, write_headers=write_header)


@patch("src.crud.requests.get")
def test_read(mock_get: Mock, crud: CRUD) -> None:
    providers = [
        ProviderRead(
            uid=uuid4(), name=random_lower_string(), type=random_provider_type()
        )
    ]
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = jsonable_encoder(providers)
    resp_body = crud.read()

    mock_get.return_value.raise_for_status.assert_not_called()
    assert len(providers) == len(resp_body)
    assert isinstance(providers[0], ProviderRead)
    assert providers[0].uid == resp_body[0].uid


@patch("src.crud.requests.post")
def test_create(mock_post: Mock, crud: CRUD) -> None:
    data = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    item = ProviderReadExtended(uid=uuid4(), **data.dict())
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = jsonable_encoder(item)
    resp_body = crud.create(data=data)

    mock_post.return_value.raise_for_status.assert_not_called()
    assert isinstance(resp_body, ProviderReadExtended)


@patch("src.crud.requests.delete")
def test_remove(mock_delete: Mock, crud: CRUD) -> None:
    item = ProviderRead(
        uid=uuid4(), name=random_lower_string(), type=random_provider_type()
    )
    mock_delete.return_value.status_code = 204
    resp_body = crud.remove(item=item)

    mock_delete.return_value.raise_for_status.assert_not_called()
    assert not resp_body


@patch("src.crud.requests.put")
def test_update(mock_put: Mock, crud: CRUD) -> None:
    old_data = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    old_item = ProviderReadExtended(uid=uuid4(), **old_data.dict())
    new_data = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    new_item = ProviderReadExtended(uid=uuid4(), **new_data.dict())
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = jsonable_encoder(new_item)
    resp_body = crud.update(new_data=new_data, old_data=old_item)

    mock_put.return_value.raise_for_status.assert_not_called()
    assert isinstance(resp_body, ProviderReadExtended)


@patch("src.crud.requests.put")
def test_update_no_changes(mock_put: Mock, crud: CRUD) -> None:
    old_data = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    old_item = ProviderReadExtended(uid=uuid4(), **old_data.dict())
    new_data = ProviderCreateExtended(
        name=random_lower_string(), type=random_provider_type()
    )
    new_item = ProviderReadExtended(uid=uuid4(), **new_data.dict())
    mock_put.return_value.status_code = 304
    mock_put.return_value.json.return_value = jsonable_encoder(new_item)
    resp_body = crud.update(new_data=new_data, old_data=old_item)

    mock_put.return_value.raise_for_status.assert_not_called()
    assert not resp_body


@parametrize_with_cases("error_code", cases=CaseErrorCode)
@parametrize_with_cases("request", cases=CaseRequest)
def test_fail_operation(request: str, error_code: int, crud: CRUD) -> None:
    with patch(f"src.crud.requests.{request}") as mock_req:
        mock_req.return_value.status_code = error_code
        execute_request(crud=crud, request=request)
        mock_req.return_value.raise_for_status.assert_called()


@parametrize_with_cases("exception", cases=CaseConnException)
@parametrize_with_cases("request", cases=CaseRequest)
def test_read_no_connection(
    request: str, exception: Union[Type[ConnectionError], Type[ReadTimeout]], crud: CRUD
) -> None:
    with patch(f"src.crud.requests.{request}") as mock_req:
        mock_req.side_effect = exception()
        with pytest.raises(exception):
            execute_request(crud=crud, request=request)
