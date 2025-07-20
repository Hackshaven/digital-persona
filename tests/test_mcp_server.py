import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_limitless_route(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless
    monkeypatch.setattr(
        limitless,
        "_search_local_entries",
        lambda start=None, end=None, keyword=None, speaker_name=None: [
            {"id": "1", "content": "hi"}
        ],
    )

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)
    resp = client.post("/limitless/lifelogs", json={})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["content"] == "hi"


def test_limitless_ignores_string_params(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless

    def fake_load(start=None, end=None, keyword=None, speaker_name=None):
        assert start is None
        assert end is None
        assert keyword is None
        assert speaker_name is None
        return [{"id": "1"}]

    monkeypatch.setattr(limitless, "_search_local_entries", fake_load)

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)

    resp = client.post(
        "/limitless/lifelogs",
        json={"start": "string", "end": "string", "keyword": "string", "speakerName": "string"},
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["id"] == "1"


def test_limitless_http_error(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "x")
    monkeypatch.setenv("MCP_PLUGINS", "digital_persona.mcp_plugins.limitless")

    import digital_persona.mcp_plugins.limitless as limitless
    from fastapi import HTTPException

    def fake_load(**_):
        raise HTTPException(status_code=400, detail="bad")

    monkeypatch.setattr(limitless, "_search_local_entries", fake_load)

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app()
    client = TestClient(app)

    resp = client.post("/limitless/lifelogs", json={})
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


def test_ai_plugin(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("MCP_PLUGINS", "")

    from digital_persona import mcp_server
    importlib.reload(mcp_server)
    app = mcp_server.create_app([])
    client = TestClient(app)

    resp = client.get("/.well-known/ai-plugin.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name_for_model"] == "limitless_mcp"
