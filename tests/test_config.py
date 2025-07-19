import importlib
import os
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


def test_load_env_searches_project_root(monkeypatch, tmp_path: Path):
    # create fake project structure with .env at root
    env_path = tmp_path / ".env"
    env_path.write_text("TEST_VAL=1\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()

    monkeypatch.chdir(scripts)
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path / "persona"))
    monkeypatch.delenv("TEST_VAL", raising=False)

    import importlib
    importlib.reload(config)

    assert os.getenv("TEST_VAL") == "1"

