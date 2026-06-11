# domstolsverket-mcp

MCP server exposing the Swedish Domstolsverket open data API over Streamable HTTP.

## Run

```sh
cp .env.example .env
uv sync
uv run main.py
```

Default endpoint: `http://0.0.0.0:8000/mcp`. Health check: `GET /health` returns `ok`. See `.env.example` for configuration.

`DOMSTOLSVERKET_MCP_API_KEY` is required — the server refuses to start without it. `.env.example` ships a throwaway local value so the steps above work out of the box.

## Deployment

Intended to run as a public HTTPS endpoint.

- **Require the API key.** Set `DOMSTOLSVERKET_MCP_API_KEY` so the MCP path requires `Authorization: Bearer <key>`. `/health` stays open for probes.
- **Put TLS in front.** The app serves plain HTTP on `:8000`. Terminate TLS ahead of it (reverse proxy or load balancer) so the bearer token is never sent in cleartext.
- DNS rebinding protection is off by design — there is no browser in the path and host-allowlisting is not access control. The API key plus TLS are.

The included `docker-compose.yml` provides this front (Traefik + Let's Encrypt): set `DOMAIN` and `ACME_EMAIL`, then `docker compose up -d`.

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
