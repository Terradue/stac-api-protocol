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

"""Exercise query decoding through ASGI rather than calling routes directly."""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from pystac import ItemCollection

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType
    from unittest.mock import Mock

    from fastapi import FastAPI
    from starlette.types import Message, Scope


@pytest.fixture
def bbox_app(api: ModuleType, service: Mock) -> Iterator[FastAPI]:
    app: FastAPI = api.app
    service.get_features.return_value = ItemCollection([])
    service.get_item_search.return_value = ItemCollection([])
    app.dependency_overrides[api.get_item_service] = lambda: service
    yield app
    app.dependency_overrides.pop(api.get_item_service)


async def _get_query(app: FastAPI, path: str, query: str) -> tuple[HTTPStatus, str]:
    """Send an HTTP query through FastAPI's complete validation pipeline."""
    response_status = HTTPStatus.INTERNAL_SERVER_ERROR
    response_body = bytearray()

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        nonlocal response_status
        if message["type"] == "http.response.start":
            response_status = HTTPStatus(message["status"])
        elif message["type"] == "http.response.body":
            response_body.extend(message["body"])

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": [],
        "server": ("localhost", 8000),
        "client": ("127.0.0.1", 1),
    }
    await app(scope, receive, send)
    return response_status, response_body.decode()


@pytest.mark.parametrize("path", ["/collections/naip/items", "/search"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", None),
        ("bbox=-103%2C40%2C102%2C42", [-103, 40, 102, 42]),
        ("bbox=-103,40,102,42", [-103, 40, 102, 42]),
        ("bbox=-103,40,0,-102,42,100", [-103, 40, 0, -102, 42, 100]),
        ("bbox=-103&bbox=40&bbox=-102&bbox=42", [-103, 40, -102, 42]),
        (
            "bbox=-103&bbox=40&bbox=0&bbox=-102&bbox=42&bbox=100",
            [-103, 40, 0, -102, 42, 100],
        ),
    ],
)
def test_bbox_query_encodings_reach_service(
    bbox_app: FastAPI, service: Mock, path: str, query: str, expected: list[float] | None
) -> None:
    datetime_value = "2022-01-01T00:00:00Z/2022-12-31T23:59:59Z"
    query += "&limit=2&datetime=2022-01-01T00%3A00%3A00Z%2F2022-12-31T23%3A59%3A59Z"
    status, body = asyncio.run(_get_query(bbox_app, path, query))
    assert status == HTTPStatus.OK
    assert json.loads(body)["type"] == "FeatureCollection"
    if path == "/search":
        service.get_item_search.assert_called_once_with(
            "http://localhost:8000", expected, None, datetime_value, 2, None, None, None
        )
    else:
        service.get_features.assert_called_once_with(
            "http://localhost:8000", "naip", 2, expected, datetime_value, None
        )


@pytest.mark.parametrize("path", ["/collections/naip/items", "/search"])
@pytest.mark.parametrize(
    "query",
    [
        "bbox=",
        "bbox=-103,40,42",
        "bbox=-103,40,-102,42,100",
        "bbox=-103,40,0,-102,42,100,200",
        "bbox=-103,40,invalid,42",
        "bbox=-103,40,,42",
        "bbox=-103,40,-102,42,",
        "bbox=-103,40,nan,42",
        "bbox=-103,40,inf,42",
        "bbox=-103,40,1e999,42",
        "bbox=-103&bbox=40&bbox=invalid&bbox=42",
    ],
)
def test_invalid_bbox_queries_do_not_reach_service(
    bbox_app: FastAPI, service: Mock, path: str, query: str
) -> None:
    status, body = asyncio.run(_get_query(bbox_app, path, query))
    assert status == HTTPStatus.UNPROCESSABLE_ENTITY
    error = json.loads(body)
    assert error["code"] == "422"
    assert "query.bbox" in error["description"]
    service.get_features.assert_not_called()
    service.get_item_search.assert_not_called()
