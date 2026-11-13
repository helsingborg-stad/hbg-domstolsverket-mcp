# domstolsverket-mcp

MCP server exposing the Swedish Domstolsverket open data API.

## Tools

| Tool | Description |
|---|---|
| `list_courts` | List courts and their court codes |
| `list_publications` | List publications, filtered by court or case number |
| `get_publication` | Get one publication by id |
| `get_publication_group` | Get related publications in a correlation group |
| `search_case_law` | Full-text search with filters (court, date, statute, keyword, publication form) |

## Run locally

```sh
cp .env.example .env
# Edit .env and set the API key
uv sync
uv run main.py
```

## Deployment

Server is deployd by [HBG MCPs](https://github.com/helsingborg-stad/hbg-mcps).
The public URL shall be `https://<MCP_DOMAIN>/domstolsverket/mcp`.
API key is requred and allowed hosts must include `MCP_DOMAIN` in production. Read `.env.example` for more info.
