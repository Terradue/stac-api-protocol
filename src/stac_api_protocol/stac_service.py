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

"""Define catalogue operations and shared landing-page metadata for service providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, final

from pystac import Link

from .models import ConformanceClasses, LandingPage

if TYPE_CHECKING:
    from geojson import GeometryCollection
    from geojson.geometry import Geometry as GeometryGeoJSON
    from pystac import Collection, Item, ItemCollection

    from .models import Collections


class StacApiService(ABC):
    """Provide shared metadata and require adopter-defined catalogue operations.

    Attributes:
        id: Stable catalogue identifier.
        title: Human-readable catalogue title.
        description: Description of the catalogue's contents.
    """

    def __init__(self, id: str, title: str, description: str) -> None:
        """Configure the identity used in the catalogue landing page."""
        self.id = id
        self.title = title
        self.description = description

    @final
    def get_landing_page(self) -> LandingPage:
        """Build metadata and links for the requested catalogue root.

        Args:
            request: Landing-page request whose URL supplies the public catalogue
                root, including any deployment prefix. Query strings are excluded.
        """
        landing_page = LandingPage(
            id=self.id,
            title=self.title,
            description=self.description,
        )

        landing_page.add_link(Link("self", "/"))
        landing_page.add_link(Link("data", "/collections"))
        landing_page.add_link(Link("conformance", "/conformance"))
        landing_page.add_link(Link("search", "/search"))
        landing_page.add_link(Link("queryables", "/queryables"))

        landing_page.conforms_to = self.get_conformance_declaration().conforms_to
        return landing_page

    @abstractmethod
    def get_collections(self) -> Collections:
        """Return the catalogue's collection listing and navigation links."""

    @abstractmethod
    def describe_collection(self, collection_id: str) -> Collection | None:
        """Return collection metadata, or None if the collection does not exist."""

    @abstractmethod
    def get_features(
        self,
        collection_id: str,
        limit: int | None,
        bbox: list[float] | None,
        datetime: str | None,
        filter: str | dict | None,
    ) -> ItemCollection | None:
        """Return matching items, an empty result, or None for an unavailable resource."""

    @abstractmethod
    def get_feature(self, collection_id: str, feature_id: str) -> Item | None:
        """Return an item, or None if it does not exist in the collection."""

    @final
    def get_conformance_declaration(self) -> ConformanceClasses:
        """Return a fresh declaration of the advertised STAC and OGC classes.

        Adopter implementations must fulfill these advertised capabilities.
        """
        return ConformanceClasses(
            conforms_to=[
                "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
                "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30",
                "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
                "http://www.opengis.net/spec/ogcapi_common-2/1.0/conf/collections",
                "http://api.stacspec.org/v1.0.0/core",
                "http://api.stacspec.org/v1.0.0/item-search",
                "https://api.stacspec.org/v1.0.0/item-search#filter",
                "http://www.opengis.net/spec/ogcapi-features-3/1.0/conf/filter",
                "http://www.opengis.net/spec/ogcapi-features-3/1.0/conf/features-filter",
                "http://www.opengis.net/spec/cql2/1.0/conf/cql2-text",
                "http://www.opengis.net/spec/cql2/1.0/conf/cql2-json",
                "http://www.opengis.net/spec/cql2/1.0/conf/basic-cql2",
                "http://www.opengis.net/spec/cql2/1.0/conf/basic-spatial-functions",
                "http://www.opengis.net/spec/cql2/1.0/conf/advanced-comparison-operators",
            ]
        )

    @abstractmethod
    def get_item_search(
        self,
        bbox: list[float] | None,
        intersects: GeometryGeoJSON | GeometryCollection | None,
        datetime: str | None,
        limit: int | None,
        ids: list[str] | None,
        collections: list[str] | None,
        filter: str | dict | None,
    ) -> ItemCollection | None:
        """Return matching items, an empty result, or None for an unavailable resource."""
