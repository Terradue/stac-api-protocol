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

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from geojson import GeometryCollection
    from geojson.geometry import Geometry as GeometryGeoJSON
    from pystac import Collection, Item, ItemCollection

    from .models import Collections, ConformanceClasses, LandingPage


class StacApiService(Protocol):
    def get_landing_page(self) -> LandingPage:
        """
        landing page
        """
        ...

    def get_collections(self) -> Collections:
        """
        the feature collections in the dataset
        """
        ...

    def describe_collection(self, collection_id: str) -> Collection | None:
        """
        describe the feature collection with id `collectionId`
        """
        ...

    def get_features(
        self, collection_id: str, limit: int | None, bbox: list[float] | None, datetime: str | None
    ) -> ItemCollection | None: ...

    def get_feature(self, collection_id: str, feature_id: str) -> Item | None:
        """
        fetch a single feature
        """
        ...

    def get_conformance_declaration(self) -> ConformanceClasses:
        """
        information about specifications that this API conforms to
        """
        ...

    def get_item_search(
        self,
        bbox: list[float] | None,
        intersects: GeometryGeoJSON | GeometryCollection | None,
        datetime: str | None,
        limit: int | None,
        ids: list[str] | None,
        collections: list[str] | None,
    ) -> ItemCollection | None: ...
