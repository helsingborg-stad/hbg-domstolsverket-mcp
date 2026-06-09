# domstolsverket-mcp

MCP server exposing the Swedish Domstolsverket open data API. Consumed by Eneo over Streamable HTTP.

## Run

```sh
cp .env.example .env
uv sync
uv run main.py
```

Default endpoint: `http://0.0.0.0:8000/mcp`. Health check: `GET /health` returns `ok`. See `.env.example` for configuration.

## Intended environment

No auth, no host filtering (DNS rebinding protection is off). Run only on a controlled private network (e.g. Elastx) behind a trusted first-party client. Do not expose it directly to the public internet!

## Upstream API

Wraps the Domstolsverket **Rättspraxis (PUH) v1** API — public, no auth.

- Base URL: `https://rattspraxis.etjanst.domstol.se`
- OpenAPI spec: [`/openapi/puh-openapi.yaml`](https://rattspraxis.etjanst.domstol.se/openapi/puh-openapi.yaml)

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/domstolar` | List courts |
| GET | `/api/v1/publiceringar` | List publications (filter by court, case number, type) |
| GET | `/api/v1/publiceringar/{id}` | Get one publication |
| GET | `/api/v1/publiceringar/grupp/{id}` | Publications in a correlation group |
| POST | `/api/v1/sok` | Full-text search with filters |
| POST | `/api/v1/sokforfiningar` | Facet counts for a search |
| GET | `/api/v1/bilagor/{lagringId}` | Stream a binary attachment (`lagringId` contains `/` — percent-encode as `%2F`) |
