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

# Install and run

Use Python 3.11 or later. Install the HTTP adapter and an ASGI server in a virtual
environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install stac-api-protocol uvicorn
```

The adapter does not include a catalogue backend. Implement and
[register a service provider](register-service.md), then install that package in
the same environment. From the provider's project directory:

```bash
python -m pip install -e .
python -m uvicorn stac_api_protocol.main:app --host 127.0.0.1 --port 8000
```

The application discovers the provider at import time. Missing or ambiguous
registrations prevent startup.

## Develop against a local adapter checkout

From the `stac-api-protocol` repository root, install the adapter in editable mode:

```bash
python -m pip install -e .
```

Install your provider and ASGI server in that environment as well. The ASGI import
path remains `stac_api_protocol.main:app`.

## Inspect the running API

- `http://127.0.0.1:8000/`: catalogue landing page supplied by your service.
- `http://127.0.0.1:8000/docs`: FastAPI's interactive API documentation.
- `http://127.0.0.1:8000/openapi.json`: the runtime OpenAPI description.

There is no `stac_api_protocol` command-line entry point. Run the application
through an ASGI server.
