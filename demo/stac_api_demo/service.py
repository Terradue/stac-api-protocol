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

"""Serve static collection metadata and query NAIP GeoParquet with DuckDB."""

from __future__ import annotations

import json
import os
from datetime import datetime as DateTime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
from pygeofilter import ast, values
from pygeofilter_duckdb import to_sql_where
from pystac import Collection, Item, ItemCollection, Link

from stac_api_protocol.models import Collections
from stac_api_protocol.stac_service import StacApiService

if TYPE_CHECKING:
    from geojson import GeometryCollection
    from geojson.geometry import Geometry as GeometryGeoJSON

# These are STAC Item top-level fields; all other Parquet columns are properties.
ITEM_FIELDS = frozenset(
    {
        "type",
        "stac_version",
        "stac_extensions",
        "id",
        "geometry",
        "bbox",
        "links",
        "assets",
        "collection",
    }
)


def _temporal_filters(datetime_value: str) -> list[ast.Node]:
    """Build inclusive time bounds for NAIP's instantaneous acquisitions."""
    start, _, end = datetime_value.partition("/")
    if not end:
        end = start
    filters: list[ast.Node] = []
    if start != "..":
        filters.append(
            ast.GreaterEqual(
                ast.Attribute("datetime"), DateTime.fromisoformat(start.upper()).isoformat()
            )
        )
    if end != "..":
        filters.append(
            ast.LessEqual(
                ast.Attribute("datetime"), DateTime.fromisoformat(end.upper()).isoformat()
            )
        )
    return filters


def _bbox_filter(bbox: list[float]) -> ast.Node:
    """Build a 2D spatial predicate, including antimeridian-crossing bounds.

    NAIP footprints have no vertical dimension; six-value boxes use XY bounds.

    Raises:
        ValueError: If the box has neither four nor six coordinates.
    """
    dimensions = len(bbox) // 2
    if dimensions not in (2, 3) or len(bbox) != dimensions * 2:
        raise ValueError("Expected four or six bbox coordinates")
    west, south, east, north = bbox[0], bbox[1], bbox[dimensions], bbox[dimensions + 1]
    geometry = ast.Attribute("geometry")
    if west > east:
        return ast.Or(
            ast.BBox(geometry, west, south, 180, north),
            ast.BBox(geometry, -180, south, east, north),
        )
    return ast.BBox(geometry, west, south, east, north)


def _read_item(payload: str) -> Item:
    """Restore nested STAC properties from a flattened GeoParquet row."""
    record = json.loads(payload)
    record["properties"] = {
        name: record.pop(name) for name in list(record) if name not in ITEM_FIELDS
    }
    # Parquet structs include null placeholders for assets absent on this item.
    record["assets"] = {
        name: asset for name, asset in record["assets"].items() if asset is not None
    }
    return Item.from_dict(record)


class GeoParquetService(StacApiService):
    """Expose the sample catalogue with NAIP as its only loaded item dataset."""

    def __init__(self, data_dir: Path) -> None:
        """Read collections.json and locate naip.parquet in a local directory.

        Args:
            data_dir: Directory populated by the demo's download script.

        Raises:
            FileNotFoundError: If either required data file is missing.
        """
        super().__init__("naip-demo", "NAIP GeoParquet demo", "NAIP imagery queried with DuckDB")
        self._parquet = data_dir / "naip.parquet"
        if not self._parquet.is_file():
            raise FileNotFoundError(f"Missing {self._parquet}; run bash download-data.sh")
        self._collections = {
            collection.id: collection
            for collection in (
                Collection.from_dict(record)
                for record in json.loads((data_dir / "collections.json").read_text())
            )
        }

    def get_collections(self) -> Collections:
        """Return all static collection descriptions, including metadata-only datasets."""
        return Collections(
            collections=[collection.clone() for collection in self._collections.values()],
            links=[Link("self", "/collections"), Link("root", "/")],
        )

    def describe_collection(self, collection_id: str) -> Collection | None:
        """Return an independent collection description, or None for an unknown ID."""
        collection = self._collections.get(collection_id)
        return collection.clone() if collection is not None else None

    def get_features(
        self,
        collection_id: str,
        limit: int | None,
        bbox: list[float] | None,
        datetime: str | None,
    ) -> ItemCollection | None:
        """Return a collection's matching items, or None for an unknown collection."""
        if collection_id not in self._collections:
            return None
        return self.get_item_search(bbox, None, datetime, limit, None, [collection_id])

    def get_feature(self, collection_id: str, feature_id: str) -> Item | None:
        """Look up an item by both collection and item ID, returning None if absent."""
        result = self.get_item_search(None, None, None, 1, [feature_id], [collection_id])
        return next(iter(result), None)

    def get_item_search(
        self,
        bbox: list[float] | None,
        intersects: GeometryGeoJSON | GeometryCollection | None,
        datetime: str | None,
        limit: int | None,
        ids: list[str] | None,
        collections: list[str] | None,
    ) -> ItemCollection:
        """Search NAIP using conjunctive filters and a deterministic, limited result.

        Unloaded collections and unmatched criteria produce an empty collection.
        The demo returns at most 10 items by default and does not paginate.
        """
        filters: list[ast.Node] = []
        for field, choices in (("id", ids), ("collection", collections)):
            if choices is not None:
                if not choices:
                    return ItemCollection([])
                filters.append(ast.In(ast.Attribute(field), list(choices), False))
        if bbox is not None:
            filters.append(_bbox_filter(bbox))
        if intersects is not None:
            filters.append(
                ast.GeometryIntersects(ast.Attribute("geometry"), values.Geometry(intersects))
            )
        if datetime is not None:
            filters.extend(_temporal_filters(datetime))
        return self._query(filters, limit if limit is not None else 10)

    def _query(self, filters: list[ast.Node], limit: int) -> ItemCollection:
        """Query using a fresh connection so concurrent requests share no cursor."""
        with duckdb.connect(config={"threads": 1}) as connection:
            connection.execute("INSTALL spatial")
            connection.load_extension("spatial")
            connection.execute("SET TimeZone = 'UTC'")
            records = connection.read_parquet(str(self._parquet))
            for predicate in filters:
                # Only server-selected fields and escaped literals reach this SQL API.
                records = records.filter(
                    to_sql_where(
                        predicate,
                        {
                            "id": "id",
                            "collection": "collection",
                            "geometry": "geometry",
                            "datetime": "datetime",
                        },
                    )
                )
            records = (
                records.order('"collection", "id"')
                .limit(limit)
                .project(
                    "* REPLACE (ST_AsGeoJSON(geometry)::JSON AS geometry, "
                    "[bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax] AS bbox)"
                )
            )
            rows = (
                records.to_view("results")
                .query("results", "SELECT to_json(results) FROM results")
                .fetchall()
            )
            return ItemCollection([_read_item(row[0]) for row in rows])


@cache
def get_service() -> GeoParquetService:
    """Load the demo service once, using STAC_DEMO_DATA_DIR or demo/data."""
    return GeoParquetService(Path(os.environ.get("STAC_DEMO_DATA_DIR", "./data")))
