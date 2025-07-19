import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_limitless_route(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless
    monkeypatch.setattr(limitless, "_fetch_entries", lambda start=None, cursor=None: ([{"id": "1", "content": "hi"}], None))

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)
    resp = client.get("/limitless/lifelogs")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["content"] == "hi"
