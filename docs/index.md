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

# STAC API Protocol

STAC API Protocol provides the HTTP layer for STAC API _Core_, _Collections_,
_Features_, and _Item Search_. It is developed according to **Hexagonal Architecture
(Ports and Adapters)** and the separation of concerns associated with **Clean
Architecture**: **FastAPI acts exclusively as the HTTP adapter**, separating the
STAC API protocol layer from the underlying data access and implementation logic.

This is particularly valuable when the purpose of an API is to make existing data sources discoverable and accessible through a standard STAC interface, without requiring the data itself to be migrated, reorganized, or managed through a new catalogue infrastructure.

![Architecture](./diagrams/architecture.svg)

## Documentation

- [First service tutorial](tutorials/first-steps.md): build and run a minimal provider.
- [Register a service factory](how-to/register-service.md): configure discovery and troubleshoot startup.
- [Install and run](how-to/install.md): prepare the runtime environment.
- [Service contract](reference/api.md): methods, return values, and HTTP behavior.
- [Architecture](explanation/architecture.md): understand the adapter boundary and dependency direction.
