from starlette.testclient import TestClient

from main import app


def test_mcp_rejects_request_without_token():
    response = TestClient(app).post("/mcp")
    assert response.status_code == 401
