import pytest
from starlette.testclient import TestClient

from main import app

AUTH = {"Authorization": "Bearer test-key"}
MCP_HEADERS = {**AUTH, "Accept": "application/json, text/event-stream"}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_mcp_rejects_request_without_token(client):
    response = client.post("/mcp")
    assert response.status_code == 401


def test_mcp_rejects_disallowed_host(client):
    headers = {**MCP_HEADERS, "Host": "evil.example.com"}
    response = client.post("/mcp", headers=headers, json=INITIALIZE)
    assert response.status_code == 421
