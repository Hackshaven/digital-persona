import importlib
from pathlib import Path
from datetime import datetime, UTC

import json

import pytest


def setup_limitless(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.setenv("LIMITLESS_API_KEY", "test-key")
    import digital_persona.mcp_plugins.limitless as limitless
    limitless = importlib.reload(limitless)
    return limitless


def test_run_once_saves_files(monkeypatch, tmp_path):
    limitless = setup_limitless(monkeypatch, tmp_path)

    def fake_fetch(*, start=None, cursor=None):
        return [
            {"id": "1", "content": "hello", "timestamp": "2025-07-07T00:00:00Z"}
        ], None

    monkeypatch.setattr(limitless, "_fetch_entries", fake_fetch)
    limitless.run_once()

    files = list(limitless.INPUT_DIR.glob("limitless-*.json"))
    assert files
    data = json.loads(files[0].read_text())
    assert data["content"] == "hello"

    state = json.loads((tmp_path / "limitless_state.json").read_text())
    assert state["start"] == "2025-07-07T00:00:00Z"
    assert state["last_id"] == "1"


def test_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    monkeypatch.delenv("LIMITLESS_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        import importlib as _imp
        _imp.reload(_imp.import_module("digital_persona.mcp_plugins.limitless"))


def test_default_start_lookback(monkeypatch, tmp_path):
    limitless = setup_limitless(monkeypatch, tmp_path)

    captured = {}

    def fake_fetch(*, start=None, cursor=None):
        captured["start"] = start
        captured["cursor"] = cursor
        return [], None

    monkeypatch.setattr(limitless, "_fetch_entries", fake_fetch)
    limitless.run_once()

    assert captured["start"] is not None
    delta = datetime.now(UTC) - datetime.fromisoformat(captured["start"].replace("Z", "+00:00"))
    assert 0 <= delta.days <= 2


def test_missing_file_triggers_redownload(monkeypatch, tmp_path):
    limitless = setup_limitless(monkeypatch, tmp_path)

    state_file = tmp_path / "limitless_state.json"
    state_file.write_text(json.dumps({"last_id": "99", "start": "2025-07-01T00:00:00Z"}))
    captured = {}

    def fake_fetch(*, start=None, cursor=None):
        captured["start"] = start
        captured["cursor"] = cursor
        return [], None

    monkeypatch.setattr(limitless, "_fetch_entries", fake_fetch)
    limitless.run_once()

    assert captured["start"] is not None
    assert captured["cursor"] is None

