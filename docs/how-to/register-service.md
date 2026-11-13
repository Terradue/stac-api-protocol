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

# Register a service factory

## Implement the port

Create a concrete implementation of `StacApiService` from
`stac_api_protocol.stac_service`. Implement every method in the
[service contract](../reference/api.md), using your own application and backend
logic. The [tutorial](../tutorials/first-steps.md) provides a complete minimal
example.

## Export the factory

In your adopter package, expose a callable that returns the configured service:

```python
# my_catalogue/provider.py
from stac_api_protocol.stac_service import StacApiService

from .service import CatalogueService


def create_service() -> StacApiService:
    """Provide the catalogue implementation used by the HTTP adapter."""
    return CatalogueService()
```

This example assumes your `CatalogueService` has a zero-argument constructor.
Adapt construction to your application's configuration and resource lifecycle.
The returned service should not require FastAPI objects to perform its operations.

## Declare the entry point

Add this table to the **adopter package's** `pyproject.toml`:

```toml
[project.entry-points."stacapi.service"]
item_service = "my_catalogue.provider:create_service"
```

| Part | Meaning |
| --- | --- |
| `stacapi.service` | Entry-point group queried by this adapter. |
| `item_service` | Required entry name for the service covering all supported routes. |
| `my_catalogue.provider` | Importable module in your installed package. |
| `create_service` | Callable factory exported by that module. |

Use the callable's name without parentheses. Despite its name, `item_service`
serves landing-page, collection, conformance, and item operations alike.

## Install and verify discovery

From your adopter project directory, install the package into the same environment
that runs the ASGI server:

```bash
python -m pip install -e .
```

Reinstall after changing entry-point metadata, and restart the server. Merely
placing the module on `PYTHONPATH` does not install entry-point metadata.

Inspect registrations without starting the application:

```python
from importlib.metadata import entry_points

for entry in entry_points(group="stacapi.service", name="item_service"):
    print(entry.name, entry.value)
```

There must be exactly one match. Start the adapter only after installing it:

```bash
python -m uvicorn stac_api_protocol.main:app --host 127.0.0.1 --port 8000
```

Install Uvicorn separately as described in [Install and run](install.md).

## Troubleshoot startup

| Failure | What to check |
| --- | --- |
| `Missing required dependency: item_service` | Install your provider in the server environment; check both the group and entry name. |
| `Multiple implementations found for: item_service` | Use an environment with only one matching provider registration. There is no automatic priority selection. |
| `Dependency is not callable: item_service` | Point at a factory function or another callable, rather than a prebuilt non-callable instance. |
| Import failure while loading the entry point | Check the module path and install your provider's runtime dependencies. Import errors propagate. |
| Failure when a request invokes the service | Check factory construction and whether the returned service implements the full protocol. Discovery alone does not check these. |
