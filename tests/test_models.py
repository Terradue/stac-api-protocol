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

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from pystac import Collection, Extent, Link, SpatialExtent, TemporalExtent

from stac_api_protocol.models import (
    Collections,
    ConformanceClasses,
    FilterLang,
    LandingPage,
    SearchBody,
)


@pytest.mark.parametrize("limit", [1, 10000, None])
def test_search_limit_accepts_boundaries(limit: int | None) -> None:
    assert SearchBody(limit=limit).limit == limit


@pytest.mark.parametrize("limit", [0, -1, 10001])
def test_search_limit_rejects_out_of_range_values(limit: int) -> None:
    with pytest.raises(ValidationError, match="limit"):
        SearchBody(limit=limit)


def test_search_defaults_and_extension_fields() -> None:
    body = SearchBody.model_validate({"custom:filter": "value"})
    assert body.model_dump() == {
        "limit": 10,
        "ids": None,
        "collections": None,
        "intersects": None,
        "datetime": None,
        "bbox": None,
        "filter": None,
        "filter_lang": FilterLang.CQL2_JSON,
        "filter_crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
        "custom:filter": "value",
    }


@pytest.mark.parametrize("field_name", ["conformsTo", "conforms_to"])
def test_conformance_accepts_alias_and_serializes_public_name(field_name: str) -> None:
    declarations = ["https://api.stacspec.org/v1.0.0/core"]
    model = ConformanceClasses.model_validate({field_name: declarations})
    assert model.conforms_to == declarations
    assert model.model_dump(by_alias=True) == {"conformsTo": declarations}


def test_landing_page_includes_conformance_declarations() -> None:
    page = LandingPage("catalog", "Example catalogue")
    page.conforms_to = ["https://api.stacspec.org/v1.0.0/core"]
    payload = page.to_dict()
    assert payload["id"] == "catalog"
    assert payload["type"] == "Catalog"
    assert payload["conformsTo"] == page.conforms_to


def test_collections_serializes_pystac_objects() -> None:
    extent = Extent(
        SpatialExtent([-180, -90, 180, 90]),
        TemporalExtent([[datetime(2024, 1, 1, tzinfo=UTC), None]]),
    )
    collection = Collection("sentinel", "Satellite imagery", extent)
    link = Link("self", "https://example.org/collections", media_type="application/json")
    model = Collections(collections=[collection], links=[link])
    assert model.model_dump(mode="json") == {
        "collections": [collection.to_dict()],
        "links": [link.to_dict()],
    }
