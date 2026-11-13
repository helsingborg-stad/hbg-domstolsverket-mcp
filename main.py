import contextlib
import secrets
import uuid
from typing import Any

import httpx
import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOMSTOLSVERKET_MCP_",
        env_file=".env",
        extra="ignore",
    )

    api_base_url: str = "https://rattspraxis.etjanst.domstol.se"
    api_timeout_seconds: float = 30.0
    api_user_agent: str = "domstolsverket-mcp/0.1"

    host: str = "0.0.0.0"
    port: int = 8000
    mcp_path: str = "/mcp"
    allowed_hosts: str = "localhost:*,127.0.0.1:*"
    allowed_origins: str = "http://localhost:*,http://127.0.0.1:*"

    api_key: str = Field(default="", validate_default=True)

    @field_validator("api_key")
    @classmethod
    def _require_api_key(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError(
                "DOMSTOLSVERKET_MCP_API_KEY must be set to a non-empty value; "
                "the MCP path requires `Authorization: Bearer <key>`."
            )
        return v


settings = Settings()

mcp = MCPServer(
    "Domstolsverket MCP",
    instructions=(
        "Use the domstolsverket tools when the user asks about Swedish case law "
        "(rättspraxis), court rulings or precedents.\n"
        "1. search_case_law with Swedish terms "
        '(e.g. and_terms=["uppsägning", "lokalhyra"]). Narrow with court_codes '
        "from list_courts, date_from/date_to, sfs_numbers or keywords.\n"
        '2. Prefer publication_forms=["REFERAT"]: referat include the full text '
        "(innehall) directly in the hits. DOM_ELLER_BESLUT hits only have a summary "
        "(sammanfattning) and metadata.\n"
        "3. typ PREJUDIKAT is precedent-setting; VAGLEDANDE_MEN_EJ_PREJUDICERANDE is "
        "guiding but not precedent-setting.\n"
        "4. get_publication(id) fetches one publication. "
        "get_publication_group(gruppKorrelationsnummer) fetches related publications, "
        "including cases cited in hanvisadePubliceringarLista.\n"
        "5. Cite the court, case number (malNummerLista), decision date "
        "(avgorandedatum) and referat number (referatNummerLista) when present."
    ),
)

http_client = httpx.AsyncClient(
    base_url=settings.api_base_url.rstrip("/"),
    timeout=settings.api_timeout_seconds,
    headers={"User-Agent": settings.api_user_agent, "Accept": "application/json"},
)


async def _get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    response = await http_client.get(path, params=params)
    response.raise_for_status()
    if not response.content:
        raise ToolError("No publication found with that id.")
    return response.json()


async def _post_json(path: str, body: dict[str, Any]) -> Any:
    response = await http_client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


@mcp.tool()
async def list_courts() -> list[dict[str, str]]:
    """List all Swedish courts that publish case law via the Domstolsverket PUH API.

    Returns a list of objects with `domstolKod` (court code, used as a filter in other
    tools) and `domstolNamn` (court name in Swedish).
    """
    return await _get_json("/api/v1/domstolar")


@mcp.tool()
async def list_publications(
    court_code: str | None = None,
    case_number: str | None = None,
    publication_types: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    sort_order: str | None = None,
    ascending: bool | None = None,
) -> list[dict[str, Any]]:
    """List case-law publications, optionally filtered by court and case number.

    Args:
        court_code: Filter by a single court's `domstolKod` (see `list_courts`).
        case_number: Filter by case number (`malnummer`).
        publication_types: Comma-separated list of publication types to include.
        page: Zero- or one-based page index (see API docs).
        page_size: Results per page.
        sort_order: Field name to sort on.
        ascending: Sort direction; true for ascending.
    """
    params = _drop_none(
        {
            "domstolkod": court_code,
            "malnummer": case_number,
            "publiceringstyper": publication_types,
            "page": page,
            "pagesize": page_size,
            "sortorder": sort_order,
            "asc": ascending,
        }
    )
    return await _get_json("/api/v1/publiceringar", params=params)


@mcp.tool()
async def get_publication(publication_id: str) -> dict[str, Any]:
    """Retrieve a single case-law publication by its id.

    The response is a PubliceringDTO with fields like `domstol`, `typ`, `avgorandedatum`,
    `sammanfattning`, `innehall`, `lagrumLista`, `nyckelordLista`, `bilagaLista`, etc.
    """
    if not _is_uuid(publication_id):
        raise ToolError("Invalid publication_id format.")
    return await _get_json(f"/api/v1/publiceringar/{publication_id}")


@mcp.tool()
async def get_publication_group(group_id: str) -> list[dict[str, Any]]:
    """Retrieve all publications sharing a correlation group id (`gruppKorrelationsnummer`)."""
    if not _is_uuid(group_id):
        raise ToolError("Invalid group_id format.")
    return await _get_json(f"/api/v1/publiceringar/grupp/{group_id}")


@mcp.tool()
async def search_case_law(
    and_terms: list[str] | None = None,
    or_terms: list[str] | None = None,
    not_terms: list[str] | None = None,
    exact_phrase: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    legal_areas: list[str] | None = None,
    sfs_numbers: list[str] | None = None,
    keywords: list[str] | None = None,
    court_codes: list[str] | None = None,
    case_numbers: list[str] | None = None,
    decision_types: list[str] | None = None,
    publication_forms: list[str] | None = None,
    page_index: int = 0,
    page_size: int = 20,
    sort_order: str | None = None,
    ascending: bool | None = None,
) -> dict[str, Any]:
    """Full-text search over Swedish higher-court case law.

    Args:
        and_terms: Terms that must all appear (AND).
        or_terms: Terms where at least one must appear (OR).
        not_terms: Terms that must not appear (NOT).
        exact_phrase: Exact phrase that must appear.
        date_from: Lower bound for `avgorandedatum` (ISO date).
        date_to: Upper bound for `avgorandedatum` (ISO date).
        legal_areas: Filter by legal area names (`rattsomrade`).
        sfs_numbers: Filter by SFS statute numbers.
        keywords: Filter by keywords (`sokord`).
        court_codes: Filter by one or more court codes (see `list_courts`).
        case_numbers: Filter by case numbers.
        decision_types: Filter by decision type (`avgorandeTyp`).
        publication_forms: Filter by publication form (`publiceringsform`); one or more of
            `REFERAT`, `DOM_ELLER_BESLUT`, `NOTIS`.
        page_index: Zero-based page index.
        page_size: Results per page.
        sort_order: Field to sort by.
        ascending: Sort direction.

    Returns:
        An object with `total` (int) and `publiceringLista` (array of publication summaries).
    """
    sokfras = _drop_none(
        {
            "andLista": and_terms,
            "orLista": or_terms,
            "notLista": not_terms,
            "exaktFras": exact_phrase,
        }
    )

    intervall = _drop_none({"fromDatum": date_from, "toDatum": date_to})
    filter_ = _drop_none(
        {
            "intervall": intervall or None,
            "rattsomradeLista": legal_areas,
            "sfsNummerLista": sfs_numbers,
            "sokordLista": keywords,
            "domstolKodLista": court_codes,
            "malnummerLista": case_numbers,
            "avgorandeTypLista": decision_types,
            "publiceringsformLista": publication_forms,
        }
    )

    body = _drop_none(
        {
            "sokfras": sokfras or None,
            "sidIndex": page_index,
            "antalPerSida": page_size,
            "sortorder": sort_order,
            "asc": ascending,
            "filter": filter_ or None,
        }
    )

    return await _post_json("/api/v1/sok", body)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


class BearerAuthMiddleware:
    """Require a matching `Authorization: Bearer <key>` on the protected path."""

    def __init__(self, app: ASGIApp, api_key: str, protected_path: str) -> None:
        self.app = app
        self.api_key = api_key.encode("utf-8")
        self.protected_path = protected_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith(self.protected_path):
            scheme, _, credentials = Headers(scope=scope).get("Authorization", "").partition(" ")
            if scheme.lower() != "bearer" or not secrets.compare_digest(
                credentials.encode("utf-8"), self.api_key
            ):
                await PlainTextResponse("Unauthorized", status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


app = mcp.streamable_http_app(
    streamable_http_path=settings.mcp_path,
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.allowed_hosts.split(","),
        allowed_origins=settings.allowed_origins.split(","),
    ),
)

# Wrap FastMCP's session-manager lifespan so the shared HTTP client closes on shutdown.
_mcp_lifespan = app.router.lifespan_context


@contextlib.asynccontextmanager
async def _lifespan(scope):
    try:
        async with _mcp_lifespan(scope):
            yield
    finally:
        await http_client.aclose()


app.router.lifespan_context = _lifespan

app.add_middleware(
    BearerAuthMiddleware,
    api_key=settings.api_key,
    protected_path=settings.mcp_path,
)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
