import copy
import os
from typing import Any, Dict, List, Type, Union
from unittest.mock import Mock, patch

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
from tests.schemas.utils import random_lower_string, random_url


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
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]
    )
    def case_error_code(self, code: int) -> int:
        return code


class CaseRespReadProviders:
    def case_empty_list(self) -> List[ProviderRead]:
        return []

    def case_providers(self, provider_read: ProviderRead) -> List[ProviderRead]:
        return [provider_read]


class CaseCRUDCreation:
    @parametrize(attr=["url", "read_headers", "write_headers"])
    def case_missing_attr(self, attr: str) -> str:
        return attr


def execute_request(
    *,
    crud: CRUD,
    request: str,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderRead,
) -> None:
    if request == "get":
        crud.read()
    elif request == "post":
        crud.create(data=provider_create)
    elif request == "delete":
        crud.remove(item=provider_read)
    elif request == "put":
        new_data = copy.deepcopy(provider_create)
        new_data.name = random_lower_string()
        crud.update(new_data=new_data, old_data=provider_read)


def crud_dict() -> Dict[str, Any]:
    """Dict with CRUD minimal attributes."""
    read_header, write_header = get_read_write_headers(token=random_lower_string())
    return {
        "url": random_url(),
        "read_headers": read_header,
        "write_headers": write_header,
    }


def test_crud_class() -> None:
    """Valid CRUD schema."""
    d = crud_dict()
    crud = CRUD(**d)
    assert crud.single_url == os.path.join(d.get("url"), "{uid}")
    assert crud.multi_url == d.get("url")
    assert crud.read_headers == d.get("read_headers")
    assert crud.write_headers == d.get("write_headers")


@parametrize_with_cases("missing_attr", cases=CaseCRUDCreation)
def test_invalid_crud_class(missing_attr: str) -> None:
    """Invalid CRUD schema.

    Missing required attributes.
    """
    d = crud_dict()
    d[missing_attr] = None
    with pytest.raises(ValueError):
        CRUD(**d)


@parametrize_with_cases("error_code", cases=CaseErrorCode)
@parametrize_with_cases("request", cases=CaseRequest)
def test_fail_operation(
    crud: CRUD,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderReadExtended,
    request: str,
    error_code: int,
) -> None:
    """Endpoint responds with error codes."""
    with patch(f"src.crud.requests.{request}") as mock_req:
        mock_req.return_value.status_code = error_code
        execute_request(
            crud=crud,
            request=request,
            provider_create=provider_create,
            provider_read=provider_read,
        )
        mock_req.return_value.raise_for_status.assert_called()


@parametrize_with_cases("exception", cases=CaseConnException)
@parametrize_with_cases("request", cases=CaseRequest)
def test_read_no_connection(
    crud: CRUD,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderReadExtended,
    request: str,
    exception: Union[Type[ConnectionError], Type[ReadTimeout]],
) -> None:
    """Connection error: no connection or read timeout."""
    with patch(f"src.crud.requests.{request}") as mock_req:
        mock_req.side_effect = exception()
        with pytest.raises(exception):
            execute_request(
                crud=crud,
                request=request,
                provider_create=provider_create,
                provider_read=provider_read,
            )


@patch("src.crud.requests.get")
@parametrize_with_cases("providers", cases=CaseRespReadProviders)
def test_read(mock_get: Mock, crud: CRUD, providers: List[ProviderRead]) -> None:
    mock_get.return_value.status_code = status.HTTP_200_OK
    mock_get.return_value.json.return_value = jsonable_encoder(providers)
    resp_body = crud.read()

    mock_get.return_value.raise_for_status.assert_not_called()
    assert len(providers) == len(resp_body)
    if len(providers) == 1:
        assert isinstance(providers[0], ProviderRead)


@patch("src.crud.requests.post")
def test_create(
    mock_post: Mock,
    crud: CRUD,
    provider_create: ProviderCreateExtended,
    provider_read_extended: ProviderReadExtended,
) -> None:
    mock_post.return_value.status_code = status.HTTP_201_CREATED
    mock_post.return_value.json.return_value = jsonable_encoder(provider_read_extended)
    resp_body = crud.create(data=provider_create)
    mock_post.return_value.raise_for_status.assert_not_called()
    assert isinstance(resp_body, ProviderReadExtended)


@patch(
    "src.crud.requests.delete",
    return_value=Mock(status_code=status.HTTP_204_NO_CONTENT),
)
def test_remove(mock_delete: Mock, crud: CRUD, provider_read: ProviderRead) -> None:
    resp_body = crud.remove(item=provider_read)
    mock_delete.return_value.raise_for_status.assert_not_called()
    assert not resp_body


@patch("src.crud.requests.put")
def test_update(
    mock_put: Mock,
    crud: CRUD,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderRead,
) -> None:
    new_create_data = copy.deepcopy(provider_create)
    new_create_data.name = random_lower_string()
    new_read_data = ProviderReadExtended(
        **new_create_data.dict(), uid=provider_read.uid
    )
    mock_put.return_value.status_code = status.HTTP_200_OK
    mock_put.return_value.json.return_value = jsonable_encoder(new_read_data)
    resp_body = crud.update(new_data=new_create_data, old_data=provider_read)
    mock_put.return_value.raise_for_status.assert_not_called()
    assert isinstance(resp_body, ProviderReadExtended)


@patch(
    "src.crud.requests.put", return_value=Mock(status_code=status.HTTP_304_NOT_MODIFIED)
)
def test_update_no_changes(
    mock_put: Mock,
    crud: CRUD,
    provider_create: ProviderCreateExtended,
    provider_read: ProviderRead,
) -> None:
    resp_body = crud.update(new_data=provider_create, old_data=provider_read)
    mock_put.return_value.raise_for_status.assert_not_called()
    assert not resp_body
