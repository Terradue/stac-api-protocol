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

from typing import TYPE_CHECKING

import pytest
from fastapi import Request
from pystac import ItemCollection

from stac_api_protocol.models import Collections
from stac_api_protocol.stac_service import StacApiService

if TYPE_CHECKING:
    from pystac import Collection, Item


class EmptyCatalogueService(StacApiService):
    """Exercise inherited metadata using a concrete empty catalogue."""

    def get_collections(self) -> Collections:
        """Return an empty collection listing."""
        return Collections(collections=[], links=[])

    def describe_collection(self, collection_id: str) -> Collection | None:
        """Report that no collection exists."""
        return None

    def get_features(
        self, collection_id: str, limit: int | None, bbox: list[float] | None, datetime: str | None
    ) -> ItemCollection | None:
        """Report that no collection exists."""
        return None

    def get_feature(self, collection_id: str, feature_id: str) -> Item | None:
        """Report that no item exists."""
        return None

    def get_item_search(self, *args: object, **kwargs: object) -> ItemCollection | None:
        """Return a successful search with no matches."""
        return ItemCollection([])


@pytest.mark.parametrize("path", ["/", "/stac/", "/stac"])
def test_landing_page_uses_request_root_without_query_string(path: str) -> None:
    service = EmptyCatalogueService(id="catalogue", title="Example", description="Example data")
    request = Request(
        {
            "type": "http",
            "scheme": "https",
            "server": ("example.org", 8443),
            "path": path,
            "query_string": b"tracking=value",
            "headers": [],
        }
    )
    page = service.get_landing_page(request)
    base_url = f"https://example.org:8443{path.rstrip('/')}"

    assert page.id == "catalogue"
    assert page.title == "Example"
    assert page.description == "Example data"
    assert {link.rel: link.get_href() for link in page.links} == {
        "root": f"{base_url}/",
        "self": f"{base_url}/",
        "data": f"{base_url}/collections",
        "conformance": f"{base_url}/conformance",
        "search": f"{base_url}/search",
    }
    assert page.to_dict()["conformsTo"] == service.get_conformance_declaration().conforms_to


def test_conformance_returns_fresh_fixed_declarations() -> None:
    service = EmptyCatalogueService("catalogue", "Example", "Example data")
    expected = [
        "https://api.stacspec.org/v1.0.0/core",
        "https://api.stacspec.org/v1.0.0/item-search",
        "https://api.stacspec.org/v1.0.0/collections",
        "https://api.stacspec.org/v1.0.0/ogcapi-features",
    ]
    assert service.get_conformance_declaration().conforms_to == expected
    service.get_conformance_declaration().conforms_to.clear()
    assert service.get_conformance_declaration().conforms_to == expected


def test_landing_page_returns_independent_metadata() -> None:
    service = EmptyCatalogueService("catalogue", "Example", "Example data")
    request = Request({"type": "http", "scheme": "https", "path": "/", "headers": []})
    page = service.get_landing_page(request)
    original = service.get_landing_page(request).to_dict()
    page.conforms_to.clear()
    page.links.clear()
    page.description = "Changed"
    assert service.get_landing_page(request).to_dict() == original
