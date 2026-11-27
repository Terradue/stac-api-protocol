# Copyright 2026 Terradue
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pystac import ItemCollection
from starlette.exceptions import HTTPException as StarletteHTTPException

from stac_api_protocol.models import SearchBody

if TYPE_CHECKING:
    from types import ModuleType
    from unittest.mock import Mock


@pytest.mark.parametrize(
    ("route", "arguments"),
    [
        ("get_landing_page", ()),
        ("get_feature", ("sentinel", "scene")),
        ("get_features", ("sentinel", 20, [1.0, 2.0, 3.0, 4.0], None, None)),
        ("get_item_search", (None, None, None, 10, None, None, None)),
    ],
)
def test_routes_serialize_service_results(
    api: ModuleType, service: Mock, http_request: Request, route: str, arguments: tuple[object, ...]
) -> None:
    backend = getattr(service, route)
    payload = {"id": "result", "links": []}
    backend.return_value.to_dict.return_value = payload
    response = getattr(api, route)(http_request, *arguments, service=service)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.body) == payload
    backend.assert_called_once_with("https://example.com/stac", *arguments)


@pytest.mark.parametrize("route", ["get_conformance_declaration"])
def test_routes_return_service_models(
    api: ModuleType, service: Mock, http_request: Request, route: str
) -> None:
    backend = getattr(service, route)
    assert getattr(api, route)(service=service) is backend.return_value
    backend.assert_called_once_with()


@pytest.mark.parametrize(
    ("route", "arguments"),
    [
        ("get_landing_page", ()),
        ("describe_collection", ("sentinel",)),
        ("get_feature", ("sentinel", "scene")),
        ("get_features", ("sentinel", 10, None, None)),
        ("get_item_search", (None, None, None, 10, None, None, None)),
    ],
)
def test_missing_results_raise_not_found(
    api: ModuleType, service: Mock, http_request: Request, route: str, arguments: tuple[object, ...]
) -> None:
    getattr(service, route).return_value = None
    with pytest.raises(HTTPException) as raised:
        getattr(api, route)(http_request, *arguments, service=service)
    assert raised.value.status_code == HTTPStatus.NOT_FOUND
    assert raised.value.detail


@pytest.mark.parametrize(
    ("route", "arguments"),
    [
        ("get_landing_page", ()),
        ("get_collections", ()),
        ("get_conformance_declaration", ()),
        ("describe_collection", ("sentinel",)),
        ("get_feature", ("sentinel", "scene")),
        ("get_features", ("sentinel", 10, None, None)),
        ("get_item_search", (None, None, None, 10, None, None, None)),
    ],
)
def test_backend_errors_become_server_errors(
    api: ModuleType, service: Mock, http_request: Request, route: str, arguments: tuple[object, ...]
) -> None:
    error = RuntimeError("backend unavailable")
    getattr(service, route).side_effect = error
    with pytest.raises(HTTPException) as raised:
        if route == "get_conformance_declaration":
            getattr(api, route)(service=service)
        else:
            getattr(api, route)(http_request, *arguments, service=service)
    assert raised.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert raised.value.__cause__ is error
    assert "backend unavailable" in raised.value.detail


@pytest.mark.parametrize("route", ["get_features", "get_item_search"])
def test_empty_item_collection_is_success(
    api: ModuleType, service: Mock, http_request: Request, route: str
) -> None:
    getattr(service, route).return_value = ItemCollection([])
    arguments = (
        ("sentinel", 10, None, None)
        if route == "get_features"
        else (None, None, None, 10, None, None)
    )
    response = getattr(api, route)(http_request, *arguments, service=service)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.body) == {"type": "FeatureCollection", "features": []}


def test_post_search_forwards_all_filters(
    api: ModuleType, service: Mock, http_request: Request
) -> None:
    geometry = '{"type":"Point","coordinates":[12,41]}'
    body = SearchBody(
        bbox=[1, 2, 3, 4],
        intersects=geometry,
        datetime="2024-01-01T00:00:00Z",
        limit=20,
        ids=["scene"],
        collections=["sentinel"],
    )
    service.get_item_search.return_value = ItemCollection([])
    response = api.post_item_search(http_request, body, service=service)
    service.get_item_search.assert_called_once_with(
        "https://example.com/stac",
        body.bbox,
        {"type": "Point", "coordinates": [12, 41]},
        body.datetime,
        body.limit,
        body.ids,
        body.collections,
        None,
    )
    assert response.status_code == HTTPStatus.OK


def test_post_search_defaults(api: ModuleType, service: Mock, http_request: Request) -> None:
    service.get_item_search.return_value = ItemCollection([])
    api.post_item_search(http_request, SearchBody(), service=service)
    service.get_item_search.assert_called_once_with(
        "https://example.com/stac", None, None, None, 10, None, None, None
    )


def test_post_search_requires_body(api: ModuleType, service: Mock, http_request: Request) -> None:
    with pytest.raises(HTTPException) as raised:
        api.post_item_search(http_request, service=service)
    assert raised.value.status_code == HTTPStatus.NOT_FOUND
    service.get_item_search.assert_not_called()


def test_http_error_handler_preserves_status_and_headers(api: ModuleType) -> None:
    error = StarletteHTTPException(
        HTTPStatus.UNAUTHORIZED, "Authentication required", {"WWW-Authenticate": "Bearer"}
    )
    response = asyncio.run(api.http_exception_handler(Request({"type": "http"}), error))
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"
    assert json.loads(response.body) == {"code": "401", "description": "Authentication required"}


def test_validation_error_handler_formats_locations(api: ModuleType) -> None:
    error = RequestValidationError(
        [
            {"loc": ("query", "limit"), "msg": "Must be positive", "type": "value_error"},
            {"loc": ("body", "bbox", 0), "msg": "Must be numeric", "type": "value_error"},
        ]
    )
    response = asyncio.run(api.validation_exception_handler(Request({"type": "http"}), error))
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.body) == {
        "code": "422",
        "description": "query.limit: Must be positive; body.bbox.0: Must be numeric",
    }


def test_unexpected_error_is_logged_but_not_exposed(
    api: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    error = RuntimeError("private backend details")
    with caplog.at_level(logging.ERROR):
        response = asyncio.run(api.unexpected_exception_handler(Request({"type": "http"}), error))
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"code": "500", "description": "Internal Server Error"}
    assert "Unhandled application error" in caplog.text
    assert caplog.records[-1].exc_info is not None
    assert caplog.records[-1].exc_info[1] is error
