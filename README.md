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

[![PyPI - Version](https://img.shields.io/pypi/v/stac-api-protocol.svg)](https://pypi.org/project/stac-api-protocol)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/stac-api-protocol.svg)](https://pypi.org/project/stac-api-protocol)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/terradue/stac-api-protocol/package.yaml?branch=develop&event=push&label=build&logo=githubactions)](https://github.com/terradue/stac-api-protocol/actions/workflows/package.yaml?query=branch%3Adevelop)
[![Code coverage](https://img.shields.io/codecov/c/github/terradue/stac-api-protocol/develop?logo=codecov)](https://app.codecov.io/gh/terradue/stac-api-protocol/tree/develop)

A Python FastAPI HTTP adapter for STAC API Core, Item Search, Features and Collections.

**Since version 0.2.0, the protocol implementation supports the
[STAC API - Filter Extension Specification v1.0.0-rc.4](https://github.com/stac-api-extensions/filter/blob/v1.0.0-rc.4/README.md).**
This includes CQL2 Text and CQL2 JSON request handling, queryables discovery, and
Filter conformance declarations. Evaluating filters against catalogue data remains
the service provider's responsibility. See the
[Filter Extension service contract](docs/reference/api.md#filter-extension-support-since-020).

## Project conventions

This project is templated a Hatch-based Python package with:

- Apache-2.0 license
- Keep a Changelog-compatible `CHANGELOG.md`
- Diátaxis documentation under `docs/`
- top-level `mkdocs.yaml`
- Taskfile integration with `Terradue/taskfile-utils`
- GitHub Actions CI

## Documentation

Project documentation is published at: 

## Contribute

Submit a [Github issue](/issues) if you have comments or suggestions.

### Local quality checks

Install [Hatch](https://hatch.pypa.io/) and [Taskfiles](https://taskfile.dev/docs/guide) then install the Git hook:

```console
task quality:pre-commit:install
```

Every commit runs Ruff (including the configured McCabe complexity limit),
Ruff formatting, strict mypy checks, and the pytest suite.

Run the complete hook explicitly with:

```console
task quality:pre-commit:run
```

## License

[![Apache License, Version 2.0](https://img.shields.io/badge/license-Apache%20License%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)

## GeoParquet demo

See [demo/README.md](demo/README.md) for a runnable NAIP-backed `StacApiService`,
Uvicorn launch command, and curl/jq examples for every API operation.
