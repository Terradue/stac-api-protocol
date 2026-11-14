# NAIP GeoParquet demo

A small `StacApiService` implementation using the existing FastAPI adapter.
Collection metadata comes from `collections.json`; item queries use DuckDB and
`pygeofilter-duckdb` over `naip.parquet` from the
[Development Seed sample data](https://github.com/developmentseed/labs-375-stac-geoparquet-backend/tree/main/data).

From the repository root, with Python 3.11 or newer:

```bash
uv venv
uv pip install -e . -e ./demo
bash demo/download-data.sh
# Install the matching DuckDB extension once (requires internet access).
uv run --no-project python -c "import duckdb; duckdb.connect().install_extension('spatial')"
uv run --no-project stac-api-demo
```

The demo has its own `pyproject.toml`, which registers the service plugin and the
`stac-api-demo` console script and declares Uvicorn and database dependencies.
Install it in an environment with no other `stacapi.service:item_service` provider.
Use `--host` and `--port` to change the default `127.0.0.1:8000` binding.
Set `STAC_DEMO_DATA_DIR` to an absolute directory to launch outside the repository.
The download script also honors this variable. Downloads are excluded from Git.

In another terminal, with `curl` and `jq` installed:

```bash
bash demo/examples.sh
# Or: bash demo/examples.sh http://127.0.0.1:9000
```

The script makes one request per API operation, including both GET and POST
search, using an actual NAIP tile and spatial/temporal bounds from the dataset.
Swagger documentation is available at `/docs`.

All five collection descriptions are exposed. Only NAIP items are loaded;
other listed collections have empty item results. Unknown collections and missing
individual items return 404. Searches support IDs, collections, bbox, intersects,
and inclusive datetime instants/intervals (including open bounds). Results are
sorted by collection and ID, default to 10 items, and have no pagination.
Six-coordinate boxes use XY only because NAIP footprints have no elevation.
The original asset and item links are preserved and may point to Planetary Computer.

This demo follows the adapter's current wire format: GET lists use repeated query
parameters, and POST `intersects` is a JSON-encoded string. It does not add a CQL
endpoint; `pygeofilter-duckdb` translates the existing search arguments internally.
Each query uses its own DuckDB connection. Runtime queries use downloaded local
files and a preinstalled spatial extension, with no external database server.

The root Hatch development and test environments install the demo automatically.
The normal format, lint, type, security, and test commands include its source and
regression tests. Tests create a tiny local GeoParquet fixture; the spatial
extension must be installed for the DuckDB version used by the test environment.

For a fresh local Hatch environment, install the extension before testing:

```bash
hatch run dev:python -c "import duckdb; duckdb.connect().install_extension('spatial')"
hatch run dev:check
hatch run test:test
```

CI installs the extension explicitly before running the tests.

Python 3.15 currently builds native dependencies from source. Its `orjson`
dependency requires Rust 1.95; use a separate toolchain without changing your
default compiler:

```bash
rustup toolchain install 1.95.0 --profile minimal
RUSTUP_TOOLCHAIN=1.95.0 hatch run +py=3.15 test:test
```
