<!--
Copyright 2026 Terradue

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Build your first service

This tutorial builds an empty catalogue provider. It demonstrates the complete
service contract and factory discovery without requiring a database. An empty
catalogue cannot demonstrate filtering or item retrieval; replace these methods
with your own application logic when connecting real data.

## 1. Create an adopter package

Create this layout in a separate directory:

```text
my-catalogue/
├── pyproject.toml
└── src/
    └── my_catalogue/
        ├── __init__.py
        └── provider.py
```

Leave `__init__.py` empty. Put the following in `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-catalogue"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["stac-api-protocol"]

[project.entry-points."stacapi.service"]
item_service = "my_catalogue.provider:create_service"

[tool.hatch.build.targets.wheel]
packages = ["src/my_catalogue"]
```

The entry point belongs to your adopter package. It tells the HTTP adapter where
to find your factory once this package is installed.

## 2. Implement the service port

Put this implementation in `src/my_catalogue/provider.py`:

```python
from geojson import GeometryCollection
from geojson.geometry import Geometry
from pystac import Collection, Item, ItemCollection, Link

from stac_api_protocol.models import Collections, ConformanceClasses, LandingPage
from stac_api_protocol.stac_service import StacApiService


class EmptyCatalogueService(StacApiService):
    """Expose an empty catalogue to demonstrate the service boundary."""

    def get_landing_page(self) -> LandingPage:
        """Describe this demonstration catalogue."""
        page = LandingPage("empty-catalogue", "An empty demonstration catalogue")
        page.conforms_to = self.get_conformance_declaration().conforms_to
        page.add_link(Link("self", "http://127.0.0.1:8000/"))
        page.add_link(Link("data", "http://127.0.0.1:8000/collections"))
        page.add_link(Link("conformance", "http://127.0.0.1:8000/conformance"))
        page.add_link(Link("search", "http://127.0.0.1:8000/search"))
        return page

    def get_collections(self) -> Collections:
        """Return the catalogue's empty collection listing."""
        return Collections(collections=[], links=[])

    def describe_collection(self, collection_id: str) -> Collection | None:
        """Report that the requested collection does not exist."""
        return None

    def get_features(
        self,
        collection_id: str,
        limit: int | None,
        bbox: list[float] | None,
        datetime: str | None,
    ) -> ItemCollection | None:
        """Report that the requested collection does not exist."""
        return None

    def get_feature(self, collection_id: str, feature_id: str) -> Item | None:
        """Report that the requested item does not exist."""
        return None

    def get_conformance_declaration(self) -> ConformanceClasses:
        """Advertise no conformance claims for this demonstration."""
        return ConformanceClasses(conformsTo=[])

    def get_item_search(
        self,
        bbox: list[float] | None,
        intersects: Geometry | GeometryCollection | None,
        datetime: str | None,
        limit: int | None,
        ids: list[str] | None,
        collections: list[str] | None,
    ) -> ItemCollection | None:
        """Return a successful search with no matching items."""
        return ItemCollection([])


def create_service() -> StacApiService:
    """Provide an empty catalogue service to the HTTP adapter."""
    return EmptyCatalogueService()
```

The class specializes `StacApiService`; the factory returns it through the port.
Neither needs to import FastAPI. All HTTP handling remains in the adapter.

The demonstration deliberately advertises no conformance classes. In a real
provider, advertise only the specifications your complete deployment implements,
and keep landing-page and conformance declarations consistent. Configure public
link URLs for your deployment instead of using these local addresses.

## 3. Install and serve

From `my-catalogue/`, create an environment and install your package and server:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . uvicorn
python -m uvicorn stac_api_protocol.main:app --host 127.0.0.1 --port 8000
```

Installation records the entry-point metadata. On application import, the adapter
finds `item_service` in the `stacapi.service` group and loads `create_service`.
FastAPI invokes the provider as a dependency when serving requests.

## 4. Exercise the adapter

In another terminal:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/collections
curl http://127.0.0.1:8000/search
curl -i http://127.0.0.1:8000/collections/missing
```

Expect a catalogue landing page, an empty collection listing, an empty GeoJSON
FeatureCollection, and an HTTP 404 for the missing collection. You can also try
these requests in `http://127.0.0.1:8000/docs`.

## 5. Connect your application

Replace `EmptyCatalogueService` with your concrete service implementation. Keep
its method signatures compatible with the [service contract](../reference/api.md),
apply the supplied filters in your application, and return the required STAC
objects. Update the factory to construct your configured implementation. The HTTP
adapter and its route definitions do not need to change.
