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

"""Check the Filter Extension contract at the model, metadata and HTTP boundaries.

Reference: https://github.com/stac-api-extensions/filter/blob/main/README.md
Sections: Conformance Classes, Queryables, GET Query Parameters and POST JSON
fields, Interaction with Endpoints, and Examples (reviewed 2026-11-25).

The provider is mocked only for HTTP forwarding tests. These tests do not certify
backend predicate evaluation, spatial/temporal algorithms or null semantics.
Predicate cases check lossless transport, not result-set evaluation.
Failures remain ordinary failures so missing requirements cannot appear certified.
"""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlsplit

import pytest
from pydantic import ValidationError
from pystac import Collection, Extent, ItemCollection, SpatialExtent, TemporalExtent

from stac_api_protocol.models import Collections, FilterLang, SearchBody
from stac_api_protocol.stac_service import StacApiService

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType
    from unittest.mock import Mock

    from fastapi import FastAPI
    from pydantic import JsonValue
    from starlette.types import Message, Scope

CRS84_URI = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
QUERYABLES_REL = "http://www.opengis.net/def/rel/ogc/1.0/queryables"
CQL2_PREFIX = "http://www.opengis.net/spec/cql2/1.0/conf/"


@pytest.fixture
def filter_app(
    api: ModuleType, service: Mock, queryables_collection: Collection
) -> Iterator[FastAPI]:
    """Isolate HTTP decoding from provider evaluation and external catalogues."""
    app: FastAPI = api.app
    service.get_item_search.return_value = ItemCollection([])
    service.get_features.return_value = ItemCollection([])
    service.describe_collection.return_value = queryables_collection
    app.dependency_overrides[api.get_item_service] = lambda: service
    try:
        yield app
    finally:
        app.dependency_overrides.pop(api.get_item_service)


async def _request(
    app: FastAPI, method: str, path: str, fields: dict[str, JsonValue]
) -> tuple[HTTPStatus, bytes, dict[bytes, bytes]]:
    """Exercise ASGI validation without introducing an HTTP-client dependency."""
    body = json.dumps(fields).encode() if method == "POST" else b""
    query = urlencode(fields).encode() if method == "GET" else b""
    response_status = HTTPStatus.INTERNAL_SERVER_ERROR
    response_body = bytearray()
    response_headers: dict[bytes, bytes] = {}

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Message) -> None:
        nonlocal response_status
        if message["type"] == "http.response.start":
            response_status = HTTPStatus(message["status"])
            response_headers.update(message["headers"])
        elif message["type"] == "http.response.body":
            response_body.extend(message["body"])

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query,
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "server": ("localhost", 8000),
        "client": ("127.0.0.1", 1),
    }
    await app(scope, receive, send)
    return response_status, bytes(response_body), response_headers


@pytest.mark.parametrize(
    "required_class",
    [
        "http://www.opengis.net/spec/ogcapi-features-3/1.0/conf/filter",
        "https://api.stacspec.org/v1.0.0/item-search#filter",
        CQL2_PREFIX + "basic-cql2",
    ],
)
def test_required_conformance_classes_are_separate_identifiers(
    service: Mock, required_class: str
) -> None:
    declaration = StacApiService.get_conformance_declaration(service)
    assert required_class in declaration.conforms_to


def test_at_least_one_cql2_encoding_is_advertised(service: Mock) -> None:
    declaration = StacApiService.get_conformance_declaration(service)
    assert {CQL2_PREFIX + "cql2-text", CQL2_PREFIX + "cql2-json"}.intersection(
        declaration.conforms_to
    )


def test_landing_page_advertises_queryables_with_standard_relation(service: Mock) -> None:
    service.id = "catalogue"
    service.title = "Test catalogue"
    service.description = "Filter compliance fixture"
    service.get_conformance_declaration.return_value = StacApiService.get_conformance_declaration(
        service
    )
    page = StacApiService.get_landing_page(service)
    assert page.to_dict()["conformsTo"] == service.get_conformance_declaration().conforms_to
    links = [link for link in page.links if link.rel == QUERYABLES_REL]
    assert links, "Landing page must advertise the OGC queryables relation"
    assert urlsplit(links[0].get_href()).path == "/queryables"


@pytest.mark.parametrize("path", ["/queryables", "/collections/sentinel/queryables"])
def test_global_and_collection_queryables_are_available(filter_app: FastAPI, path: str) -> None:
    status, body, headers = asyncio.run(_request(filter_app, "GET", path, {}))
    assert status == HTTPStatus.OK
    assert headers[b"content-type"].split(b";")[0] == b"application/schema+json"
    schema = json.loads(body)
    assert schema["type"] == "object"
    assert schema["$schema"].startswith("https://json-schema.org/")
    assert urlsplit(schema["$id"]).path == path
    assert isinstance(schema["properties"], dict)
    assert all(not name.startswith("properties.") for name in schema["properties"])
    if not schema["properties"]:
        assert schema["additionalProperties"] is True


@pytest.mark.parametrize("filter_lang", [None, "cql2-json"])
def test_post_model_defaults_to_cql2_json_and_crs84(filter_lang: str | None) -> None:
    fields: dict[str, JsonValue] = {"filter": {"op": "=", "args": [{"property": "id"}, "scene"]}}
    if filter_lang is not None:
        fields["filter-lang"] = filter_lang
    body = SearchBody.model_validate(fields)
    assert body.filter_lang == FilterLang.CQL2_JSON
    assert body.filter_crs == CRS84_URI
    assert body.model_dump(mode="json", by_alias=True)["filter"] == fields["filter"]
    assert body.model_dump(mode="json", by_alias=True)["filter-crs"] == CRS84_URI


@pytest.mark.parametrize(
    "fields",
    [
        {"filter-lang": "cql-json"},
        {"filter-lang": "sql"},
        {"filter-crs": "EPSG:4326"},
        {"filter-crs": "http://www.opengis.net/def/crs/EPSG/0/3857"},
    ],
)
def test_post_model_rejects_invalid_language_and_crs(fields: dict[str, JsonValue]) -> None:
    with pytest.raises(ValidationError):
        SearchBody.model_validate(fields)


@pytest.mark.parametrize("path", ["/search", "/collections/sentinel/items"])
@pytest.mark.parametrize("filter_lang", [None, "cql2-text"])
def test_get_defaults_to_text_and_decodes_escaped_expression(
    filter_app: FastAPI, service: Mock, path: str, filter_lang: str | None
) -> None:
    expression = "id = 'scene + 1' AND eo:cloud_cover <= 10"
    fields: dict[str, JsonValue] = {"filter": expression, "filter-crs": CRS84_URI}
    if filter_lang is not None:
        fields["filter-lang"] = filter_lang
    status, body, _ = asyncio.run(_request(filter_app, "GET", path, fields))
    assert status == HTTPStatus.OK
    assert json.loads(body) == {"type": "FeatureCollection", "features": []}
    if path == "/search":
        service.get_item_search.assert_called_once_with(
            None, None, None, 10, None, None, expression
        )
    else:
        service.get_features.assert_called_once_with("sentinel", 10, None, None, expression)


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param({"op": operator, "args": [{"property": "eo:cloud_cover"}, 10]}, id=operator)
        for operator in ("=", "<>", "<", "<=", ">", ">=")
    ]
    + [
        pytest.param({"op": "isNull", "args": [{"property": "missing"}]}, id="is-null"),
        pytest.param(
            {"op": "not", "args": [{"op": "=", "args": [{"property": "id"}, "scene"]}]},
            id="not",
        ),
    ]
    + [
        pytest.param(
            {
                "op": operator,
                "args": [
                    {"op": "=", "args": [{"property": "id"}, "scene"]},
                    {"op": "=", "args": [{"property": "collection"}, "sentinel"]},
                ],
            },
            id=operator,
        )
        for operator in ("and", "or")
    ],
)
def test_cql2_json_basic_predicates_reach_service(
    filter_app: FastAPI, service: Mock, method: str, expression: JsonValue
) -> None:
    fields: dict[str, JsonValue] = {
        "filter": json.dumps(expression) if method == "GET" else expression,
        "filter-lang": "cql2-json",
    }
    status, _, _ = asyncio.run(_request(filter_app, method, "/search", fields))
    assert status == HTTPStatus.OK
    service.get_item_search.assert_called_once_with(None, None, None, 10, None, None, expression)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_filter_is_combined_with_standard_search_constraints(
    filter_app: FastAPI, service: Mock, method: str
) -> None:
    expression: JsonValue = {"op": "<=", "args": [{"property": "eo:cloud_cover"}, 10]}
    fields: dict[str, JsonValue] = {
        "filter": json.dumps(expression) if method == "GET" else expression,
        "filter-lang": "cql2-json",
        "filter-crs": CRS84_URI,
        "bbox": "1,2,3,4" if method == "GET" else [1, 2, 3, 4],
        "datetime": "2024-01-01T00:00:00Z",
        "limit": 2,
        "ids": "scene" if method == "GET" else ["scene"],
        "collections": "sentinel" if method == "GET" else ["sentinel"],
    }
    status, _, _ = asyncio.run(_request(filter_app, method, "/search", fields))
    assert status == HTTPStatus.OK
    service.get_item_search.assert_called_once_with(
        [1, 2, 3, 4], None, fields["datetime"], 2, ["scene"], ["sentinel"], expression
    )


@pytest.mark.parametrize("path", ["/search", "/collections/sentinel/items"])
@pytest.mark.parametrize("expression", ["{", '{"op":"unknown","args":[]}', '{"op":"="}'])
def test_malformed_cql2_json_get_returns_bad_request(
    filter_app: FastAPI, service: Mock, path: str, expression: str
) -> None:
    status, body, _ = asyncio.run(
        _request(filter_app, "GET", path, {"filter": expression, "filter-lang": "cql2-json"})
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert json.loads(body)["description"]
    service.get_item_search.assert_not_called()
    service.get_features.assert_not_called()


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_search_without_filter_remains_available(
    filter_app: FastAPI, service: Mock, method: str
) -> None:
    status, _, _ = asyncio.run(_request(filter_app, method, "/search", {}))
    assert status == HTTPStatus.OK
    service.get_item_search.assert_called_once_with(None, None, None, 10, None, None, None)


@pytest.mark.parametrize("operator", ["=", "<>", "<", "<=", ">", ">="])
@pytest.mark.parametrize(
    "literal",
    ["scene", 10, True, {"date": "2024-01-01"}, {"timestamp": "2024-01-01T00:00:00Z"}],
)
def test_basic_comparison_literals_survive_post_model_round_trip(
    operator: str, literal: JsonValue
) -> None:
    expression: JsonValue = {"op": operator, "args": [{"property": "value"}, literal]}
    body = SearchBody.model_validate({"filter": expression})
    assert body.model_dump(mode="json", by_alias=True, exclude_unset=True)["filter"] == expression


@pytest.mark.parametrize("expression", [True, False])
def test_boolean_cql2_expressions_survive_post_model_round_trip(expression: bool) -> None:
    body = SearchBody.model_validate({"filter": expression})
    assert body.model_dump(mode="json", by_alias=True, exclude_unset=True)["filter"] is expression


@pytest.mark.parametrize("filter_lang", [None, "cql2-json"])
def test_post_json_filter_uses_default_encoding(
    filter_app: FastAPI, service: Mock, filter_lang: str | None
) -> None:
    expression: JsonValue = {"op": "=", "args": [{"property": "id"}, "scene"]}
    fields: dict[str, JsonValue] = {"filter": expression}
    if filter_lang is not None:
        fields["filter-lang"] = filter_lang
    status, _, _ = asyncio.run(_request(filter_app, "POST", "/search", fields))
    assert status == HTTPStatus.OK
    service.get_item_search.assert_called_once_with(None, None, None, 10, None, None, expression)


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    "fields",
    [{"filter-lang": "sql"}, {"filter-crs": "EPSG:3857"}],
)
def test_invalid_filter_parameters_are_rejected_before_provider_call(
    filter_app: FastAPI, service: Mock, method: str, fields: dict[str, JsonValue]
) -> None:
    status, body, _ = asyncio.run(_request(filter_app, method, "/search", fields))
    assert status in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY)
    assert json.loads(body)["description"]
    service.get_item_search.assert_not_called()


def test_post_text_is_processed_or_explicitly_rejected(filter_app: FastAPI, service: Mock) -> None:
    expression = "id = 'scene'"
    status, _, _ = asyncio.run(
        _request(filter_app, "POST", "/search", {"filter": expression, "filter-lang": "cql2-text"})
    )
    # The README permits omitting POST text support, but requires a 400 response.
    if status == HTTPStatus.BAD_REQUEST:
        service.get_item_search.assert_not_called()
    else:
        assert status == HTTPStatus.OK
        service.get_item_search.assert_called_once_with(
            None, None, None, 10, None, None, expression
        )


def test_filter_routes_generate_openapi_with_string_get_filters(api: ModuleType) -> None:
    schema = api.app.openapi()
    for path in ("/search", "/collections/{collectionId}/items"):
        parameters = schema["paths"][path]["get"]["parameters"]
        parameter = next(entry for entry in parameters if entry["name"] == "filter")
        assert parameter["in"] == "query"
        assert {"type": "string"} in parameter["schema"]["anyOf"]
    error_schema = schema["paths"]["/queryables"]["get"]["responses"]["default"]["content"][
        "application/json"
    ]["schema"]
    assert error_schema == {"$ref": "#/components/schemas/Exception"}


@pytest.fixture
def queryables_collection() -> Collection:
    """Provide real metadata while keeping all provider operations mocked."""
    return Collection(
        "sentinel",
        "Test collection",
        Extent(SpatialExtent([-180, -90, 180, 90]), TemporalExtent([None, None])),
    )


@pytest.mark.parametrize("path", ["/queryables", "/collections/sentinel/queryables"])
def test_queryables_identity_excludes_query_string(filter_app: FastAPI, path: str) -> None:
    status, body, _ = asyncio.run(_request(filter_app, "GET", path, {"unused": "value"}))
    assert status == HTTPStatus.OK
    schema = json.loads(body)
    assert schema["$id"] == "http://localhost:8000" + path
    assert "filter" not in schema["properties"]
    assert {"id", "collection", "geometry", "datetime"} <= schema["properties"].keys()


@pytest.mark.parametrize("path", ["/collections/sentinel", "/collections"])
def test_collection_responses_advertise_queryables_without_mutating_provider_metadata(
    filter_app: FastAPI, service: Mock, queryables_collection: Collection, path: str
) -> None:
    service.get_collections.return_value = Collections(
        collections=[queryables_collection], links=[]
    )
    original = queryables_collection.to_dict()
    status, body, _ = asyncio.run(_request(filter_app, "GET", path, {}))
    assert status == HTTPStatus.OK
    payload = json.loads(body)
    collection = payload["collections"][0] if path == "/collections" else payload
    links = [link for link in collection["links"] if link["rel"] == QUERYABLES_REL]
    assert links == [
        {
            "rel": QUERYABLES_REL,
            "href": "/collections/sentinel/queryables",
            "type": "application/schema+json",
        }
    ]
    assert queryables_collection.to_dict() == original


def test_unknown_collection_queryables_returns_not_found(
    filter_app: FastAPI, service: Mock
) -> None:
    service.describe_collection.return_value = None
    status, body, _ = asyncio.run(
        _request(filter_app, "GET", "/collections/unknown/queryables", {})
    )
    assert status == HTTPStatus.NOT_FOUND
    assert json.loads(body)["code"] == "404"
    service.describe_collection.assert_called_once_with("unknown")


def test_collection_queryables_provider_failure_returns_server_error(
    filter_app: FastAPI, service: Mock
) -> None:
    service.describe_collection.side_effect = RuntimeError("private details")
    status, body, _ = asyncio.run(
        _request(filter_app, "GET", "/collections/sentinel/queryables", {})
    )
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body)["code"] == "500"
    assert "private details" not in body.decode()


def test_queryables_openapi_advertises_schema_media_type(api: ModuleType) -> None:
    for path in ("/queryables", "/collections/{collectionId}/queryables"):
        response = api.app.openapi()["paths"][path]["get"]["responses"]["200"]
        assert set(response["content"]) == {"application/schema+json"}
