# NAIP GeoParquet demo

A small `StacApiService` implementation using the existing FastAPI adapter.
Collection metadata comes from `collections.json`; item queries use DuckDB and
`pygeofilter-duckdb` over `naip.parquet` from the
[Development Seed sample data](https://github.com/developmentseed/labs-375-stac-geoparquet-backend/tree/main/data).

From the repository root, with Python 3.11 or newer:

```bash
cd demo
uv venv
uv pip install -e .. -e .

bash ./download-data.sh
bash ./start.sh
```

The demo has its own `pyproject.toml`, which registers the service plugin and
declares Uvicorn and database dependencies. `demo/start.sh` runs Uvicorn directly
and forwards all arguments to it.
Install it in an environment with no other `stacapi.service:item_service` provider.
Set `STAC_DEMO_DATA_DIR` to an absolute directory to launch outside the repository.
The download script also honors this variable. Downloads are excluded from Git.

In another terminal, with `curl` and `jq` installed:

```bash
bash demo/examples.sh
# Or: bash demo/examples.sh http://127.0.0.1:8090
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

GET `bbox` accepts comma-separated coordinates or repeated query parameters.
Other GET lists use repeated query parameters, and POST `intersects` is a
JSON-encoded string. It does not add a CQL
endpoint; `pygeofilter-duckdb` translates the existing search arguments internally.
Each query uses its own DuckDB connection. Runtime queries use downloaded local
files and a preinstalled spatial extension, with no external database server.
