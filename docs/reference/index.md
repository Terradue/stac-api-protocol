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

# Reference

Adopters provide the application behavior by implementing `StacApiService`, the
service port defined in `src/stac_api_protocol/stac_service.py`. Your service
connects catalogue operations to your domain logic, storage, and search systems.
This package supplies the routes, request validation, response serialization,
and HTTP error handling.

## Integration at a glance

1. Subclass `StacApiService` and implement its five abstract catalogue operations.
2. Expose a callable factory that returns your service implementation.
3. Register that factory in your package's `pyproject.toml`:

   ```toml
   [project.entry-points."stacapi.service"]
   item_service = "my_catalogue.provider:create_service"
   ```

4. Install your package alongside `stac-api-protocol`, then serve
   `stac_api_protocol.main:app` with an ASGI server.

The entry-point group **`stacapi.service`** and entry name **`item_service`** are
required. The module and factory names on the right-hand side are yours to choose.
Exactly one installed provider must match. Installing this HTTP adapter alone
does not supply a catalogue backend.

[Service contract](api.md) documents the `StacApiService` operations, their HTTP
routes, result semantics, and provider discovery.
