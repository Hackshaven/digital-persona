import importlib
from pathlib import Path
import json

from digital_persona import config


def test_enabled_services_env(monkeypatch):
    monkeypatch.setenv("ENABLED_SERVICES", "foo,bar")
    assert config.enabled_services() == ["foo", "bar"]


def test_enabled_services_file(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ENABLED_SERVICES", raising=False)
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    cfg = {"enabled_services": ["x", "y"]}
    (tmp_path / "persona_config.json").write_text(json.dumps(cfg))
    importlib.reload(config)
    assert config.enabled_services() == ["x", "y"]

