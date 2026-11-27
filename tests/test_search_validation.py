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

import json
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import HTTPException, Request
from pystac import ItemCollection

from stac_api_protocol.models import SearchBody

if TYPE_CHECKING:
    from types import ModuleType
    from unittest.mock import Mock


@pytest.mark.parametrize("method", ["features", "get", "post"])
@pytest.mark.parametrize(
    "datetime_value",
    [
        None,
        "2024-02-29T12:30:00Z",
        "2024-02-29t12:30:00.123z",
        "2024-01-01T12:00:00+02:30",
        "2024-01-01T12:00:00-03:00",
        "../2024-01-01T00:00:00Z",
        "2024-01-01T00:00:00Z/..",
        "2024-01-01T00:00:00Z/2024-01-01T00:00:00Z",
        "2024-01-01T01:00:00+02:00/2024-01-01T00:00:00Z",
    ],
)
def test_valid_datetimes_reach_service(
    api: ModuleType, service: Mock, http_request: Request, method: str, datetime_value: str | None
) -> None:
    service.get_features.return_value = ItemCollection([])
    service.get_item_search.return_value = ItemCollection([])
    if method == "features":
        api.get_features(http_request, "sentinel", 10, None, datetime_value, service=service)
        service.get_features.assert_called_once_with(
            "https://example.com/stac", "sentinel", 10, None, datetime_value, None
        )
    elif method == "get":
        api.get_item_search(
            http_request, None, None, datetime_value, 10, None, None, service=service
        )
        service.get_item_search.assert_called_once_with(
            "https://example.com/stac", None, None, datetime_value, 10, None, None, None
        )
    else:
        api.post_item_search(http_request, SearchBody(datetime=datetime_value), service=service)
        service.get_item_search.assert_called_once_with(
            "https://example.com/stac", None, None, datetime_value, 10, None, None, None
        )


@pytest.mark.parametrize("method", ["features", "get", "post"])
@pytest.mark.parametrize(
    "datetime_value",
    [
        "",
        "..",
        "../..",
        "2024-01-01",
        "2024-01-01T00:00:00",
        "2023-02-29T00:00:00Z",
        "2024-01-01T24:00:00Z",
        "2024-01-01 00:00:00Z",
        "2024-01-01T00:00:00+24:00",
        "2024-01-01T00:00:00Z/",
        "2024-01-01T00:00:00Z/../..",
        "2024-01-02T00:00:00Z/2024-01-01T00:00:00Z",
    ],
)
def test_invalid_datetimes_are_rejected_before_service_call(
    api: ModuleType, service: Mock, http_request: Request, method: str, datetime_value: str
) -> None:
    with pytest.raises(HTTPException) as raised:
        if method == "features":
            api.get_features(http_request, "sentinel", 10, None, datetime_value, service=service)
        elif method == "get":
            api.get_item_search(
                http_request, None, None, datetime_value, 10, None, None, service=service
            )
        else:
            api.post_item_search(http_request, SearchBody(datetime=datetime_value), service=service)
    assert raised.value.status_code == HTTPStatus.BAD_REQUEST
    assert raised.value.detail.startswith("Invalid datetime:")
    service.get_features.assert_not_called()
    service.get_item_search.assert_not_called()


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    "geometry",
    [
        "not json",
        "{}",
        "[]",
        '"text"',
        '{"type":"Feature","geometry":{"type":"Point","coordinates":[1,2]},"properties":{}}',
        '{"type":"Point","coordinates":[1]}',
        '{"type":"Polygon","coordinates":[[[0,0],[1,1]]]}',
    ],
)
def test_invalid_geometries_are_rejected_before_service_call(
    api: ModuleType, service: Mock, http_request: Request, method: str, geometry: str
) -> None:
    with pytest.raises(HTTPException) as raised:
        if method == "get":
            api.get_item_search(http_request, None, geometry, None, 10, None, None, service=service)
        else:
            api.post_item_search(http_request, SearchBody(intersects=geometry), service=service)
    assert raised.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert raised.value.detail == "Invalid intersects geometry"
    service.get_item_search.assert_not_called()


@pytest.mark.parametrize(
    "geometry",
    [
        '{"type":"Point","coordinates":[12,41]}',
        '{"type":"GeometryCollection","geometries":[{"type":"Point","coordinates":[12,41]}]}',
        "null",
    ],
)
def test_get_search_parses_geometry(
    api: ModuleType, service: Mock, http_request: Request, geometry: str
) -> None:
    service.get_item_search.return_value = ItemCollection([])
    api.get_item_search(
        http_request, None, geometry, None, 10, ["scene"], ["sentinel"], service=service
    )
    service.get_item_search.assert_called_once_with(
        "https://example.com/stac",
        None,
        json.loads(geometry),
        None,
        10,
        ["scene"],
        ["sentinel"],
        None,
    )
