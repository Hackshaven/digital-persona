import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_limitless_route(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless
    monkeypatch.setattr(limitless, "_fetch_entries", lambda start=None, cursor=None, api_key="x": ([{"id": "1", "content": "hi"}], None))

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)
    resp = client.post("/limitless/lifelogs?api_key=x", json={})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["content"] == "hi"


def test_limitless_ignores_string_params(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless

    def fake_fetch(start=None, cursor=None, api_key="x"):
        assert start is None
        assert cursor is None
        return [{"id": "1"}], None

    monkeypatch.setattr(limitless, "_fetch_entries", fake_fetch)

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)

    resp = client.post(
        "/limitless/lifelogs?api_key=x", json={"start": "string", "cursor": "string"}
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["id"] == "1"


def test_limitless_http_error(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless
    import httpx

    def fake_fetch(**_):
        request = httpx.Request("GET", "http://x")
        response = httpx.Response(400, request=request, text="bad")
        raise httpx.HTTPStatusError("bad", request=request, response=response)

    monkeypatch.setattr(limitless, "_fetch_entries", fake_fetch)

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)

    resp = client.post("/limitless/lifelogs?api_key=x", json={})
    assert resp.status_code == 400


def test_root_route(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("MCP_PLUGINS", "")

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app([])
    client = TestClient(app)

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"].startswith("MCP server")
