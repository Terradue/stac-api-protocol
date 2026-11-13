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

# Service contract

Adopters implement `StacApiService`, defined in
`src/stac_api_protocol/stac_service.py`. The HTTP adapter invokes its synchronous
methods with parsed filter values. All seven operations belong to the same
registered `item_service` provider.

## Operations and routes

| HTTP route | Service method | Return type |
| --- | --- | --- |
| `GET /` | `get_landing_page()` | `LandingPage` |
| `GET /collections` | `get_collections()` | `Collections` |
| `GET /collections/{collectionId}` | `describe_collection(collection_id)` | `pystac.Collection` or `None` |
| `GET /collections/{collectionId}/items` | `get_features(collection_id, limit, bbox, datetime)` | `pystac.ItemCollection` or `None` |
| `GET /collections/{collectionId}/items/{featureId}` | `get_feature(collection_id, feature_id)` | `pystac.Item` or `None` |
| `GET /conformance` | `get_conformance_declaration()` | `ConformanceClasses` |
| `GET /search`, `POST /search` | `get_item_search(bbox, intersects, datetime, limit, ids, collections)` | `pystac.ItemCollection` or `None` |

`LandingPage`, `Collections`, and `ConformanceClasses` come from
`stac_api_protocol.models`. Use these existing types rather than creating
parallel representations of the HTTP contract.

## Filter and result semantics

- `bbox` is a list of numbers or `None`; `ids` and `collections` are lists of strings
  or `None`.
- `datetime` is a string or `None`. The adapter validates timezone-qualified
  RFC 3339 instants and intervals before delegation. Open interval bounds use
  `..`; both bounds cannot be open, and closed bounds must be ordered.
- `intersects` reaches the service as a GeoJSON geometry or geometry collection,
  or `None`. In the current implementation, both the GET parameter and the POST
  `SearchBody.intersects` field accept a **JSON-encoded string**. The adapter parses
  that string before invoking the service.
- The default `limit` is 10; HTTP validation constrains supplied numeric limits
  to 1–10000. The service signature also permits `None`.
- Applying filters, choosing items, and constructing result links are the
  adopter's responsibility. Passing validation does not execute a search.
- Return `ItemCollection([])` for a successful search with no matches. Returning
  `None` from an item-list or search operation causes an HTTP 404 response.
- Return `None` for a missing collection or individual item. The adapter maps it
  to HTTP 404.
- Set `LandingPage.conforms_to` explicitly. Its serializer adds `conformsTo` to
  the catalogue JSON. `ConformanceClasses` exposes `conforms_to` in Python and
  the `conformsTo` alias in JSON.
- `Collections` wraps PySTAC collections and links and serializes them to JSON.

The landing-page contract requires a `LandingPage`, although the route also maps
an absent result to HTTP 404. Collection-list and conformance methods must return
their declared models.

## Errors

Malformed datetime filters produce HTTP 400. Invalid geometry strings and request
validation failures produce HTTP 422. Service exceptions caught by the route
handlers become HTTP 500; their current descriptions include the exception text.
Avoid putting sensitive data in exceptions that cross this boundary. Unhandled
application exceptions are logged and receive a generic HTTP 500 response.

HTTP error bodies use the package's STAC exception model with `code` and
`description` fields. Service implementations should express normal missing
resources through the optional return values above; they do not need to construct
FastAPI responses or raise FastAPI exceptions.

## Python protocol

::: stac_api_protocol.stac_service.StacApiService

## Provider discovery

::: stac_api_protocol.plugin_loader.load_dependency

See [Register a service factory](../how-to/register-service.md) for packaging
metadata and startup diagnostics.
