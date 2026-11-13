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

# Architecture: Ports and Adapters

STAC API Protocol is developed according to **Hexagonal Architecture (Ports and
Adapters)**. It follows the same separation of application behavior from delivery
mechanisms emphasized by **Clean Architecture**. These are closely related
architectural approaches; here their practical consequence is that **FastAPI
acts exclusively as the HTTP adapter**.

## The service port

`StacApiService`, defined in `src/stac_api_protocol/stac_service.py`, is the boundary
between the HTTP adapter and an adopter's catalogue application. It is an abstract base class with five adopter-defined catalogue operations and
two final metadata methods. Adopters subclass it and supply a catalogue identifier,
title, and description. Incomplete subclasses cannot be instantiated.

The shared landing-page method receives a FastAPI `Request` to derive public
links. This is an HTTP coupling in the current service contract; catalogue search
and retrieval operations remain independent of FastAPI request objects. The
conformance method returns a fixed declaration of the four bundled STAC API
classes, which each adopter must implement.

```text
HTTP client
    |
    v
FastAPI HTTP adapter (stac_api_protocol.main)
    |
    | calls the StacApiService port
    v
Adopter's service implementation
    |
    v
Application/domain logic and backend integrations
    |
    v
Catalogue storage, search engine, or remote services
```

This diagram shows request flow. The HTTP adapter depends on the service contract;
it does not import a concrete adopter implementation. The adopter supplies that
implementation at runtime through an installed Python entry point.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| FastAPI HTTP adapter | Route requests, parse and validate HTTP inputs, invoke the service, serialize results, and translate failures into HTTP responses. |
| `StacApiService` port | Define the operations and data types required by the adapter. |
| Adopter's service | Implement catalogue use cases, filtering, lookup, and result construction; coordinate domain logic and backend access. |
| Adopter's backend integrations | Access databases, indexes, files, or remote services as required by the application. |
| Provider factory | Construct or obtain a configured service and supply it to the HTTP adapter. |

Keep FastAPI responses and dependency injection out of your catalogue business
logic. Apart from the shared landing-page method, service methods receive ordinary
filter values and return the
STAC objects specified by the port. If your domain uses different objects, map
them to these types at the service boundary. The port intentionally uses PySTAC,
GeoJSON, and package models; it is a STAC-facing contract, not a universal domain
model.

## Runtime composition

When `stac_api_protocol.main` is imported, `load_dependency("item_service")`
looks up installed entry points in the `stacapi.service` group. It loads the
unique matching callable. FastAPI then uses that callable through `Depends`
to obtain the service for route execution.

Discovery loads the factory; it does not call it to create a global service.
Do not assume the adapter constructs a singleton or manages your backend's
connection lifecycle. Your provider and deployment must choose the appropriate
resource lifetime. A simple zero-argument factory is sufficient to get started.

The loader checks that there is exactly one matching entry and that it is
callable. It does not validate the returned object's implementation of the service contract.
Type-check and test your implementation against the service contract.

See [factory registration](../how-to/register-service.md) for the exact metadata
and [the tutorial](../tutorials/first-steps.md) for a runnable example.

## Schema-first HTTP contracts

The OpenAPI schema under `schemas/` is the source of truth for generated API
artifacts. Adopters should reuse the existing models and implement the service
port instead of editing generated routes or models to attach a backend. Changes
to schema-defined contracts belong in the schema and the repository's configured
generation workflow.
