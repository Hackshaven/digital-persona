import json
import os
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from werkzeug.utils import secure_filename

if "langchain" not in sys.modules:
    class FakeMessage:
        def __init__(self, content):
            self.content = content

    schema_mod = types.SimpleNamespace(HumanMessage=FakeMessage, SystemMessage=FakeMessage)
    sys.modules["langchain_core"] = types.SimpleNamespace(messages=schema_mod)
    sys.modules["langchain_core.messages"] = schema_mod
    chat_models = types.SimpleNamespace(ChatOpenAI=object)
    sys.modules["langchain"] = types.SimpleNamespace(chat_models=chat_models, schema=schema_mod)
    sys.modules["langchain.chat_models"] = chat_models
    sys.modules["langchain.schema"] = schema_mod
    sys.modules["langchain_openai"] = types.SimpleNamespace(ChatOpenAI=object)
    sys.modules["langchain_ollama"] = types.SimpleNamespace(ChatOllama=object)

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))


class StubInterviewer:
    def __init__(self):
        self.trait_names = ["openness", "conscientiousness"]

    def generate_questions(self, notes):
        return ["Q1?", "Q2?"]

    def generate_followup(self, q, a):
        return "Clarify?"

    def profile_from_answers(self, notes, qa_pairs):
        return {"notes": notes, "interview": qa_pairs, "traits": {"openness": 0.5}}


@pytest.fixture()
def persona_env(monkeypatch):
    with TemporaryDirectory() as td:
        monkeypatch.setenv("PERSONA_DIR", td)
        yield Path(td)


@pytest.fixture()
def api_module(persona_env):
    import importlib
    import digital_persona.api as api
    api = importlib.reload(api)
    yield api


@pytest.fixture()
def client(api_module):
    app = api_module.create_app(StubInterviewer())
    return TestClient(app)


def test_generate_questions_endpoint(client):
    resp = client.post("/generate_questions", json={"notes": "text"})
    assert resp.status_code == 200
    assert resp.json()["questions"] == ["Q1?", "Q2?"]


def test_profile_from_answers_returns_profile_without_saving(client, api_module):
    qa = [{"question": "Q1", "answer": "A1"}]
    resp = client.post("/profile_from_answers", json={"notes": "txt", "qa": qa})
    assert resp.status_code == 200
    prof = resp.json()
    assert prof["traits"]["openness"] == 0.5
    assert not (api_module.PERSONA_DIR / "profile.json").exists()


def test_memory_save_and_timeline(client):
    resp = client.post("/memory/save", json={"text": "note"})
    assert resp.status_code == 200
    ts = resp.json()["timestamp"]

    timeline = client.get("/memory/timeline").json()
    assert any(m["timestamp"] == ts for m in timeline)


def test_memory_file_encrypted(client, api_module):
    resp = client.post("/memory/save", json={"text": "secret"})
    ts = resp.json()["timestamp"]
    safe_ts = secure_filename(ts.replace(":", "-"))
    path = api_module.MEMORY_DIR / f"{safe_ts}.json"
    raw = path.read_bytes()
    assert not raw.lstrip().startswith(b"{")


def test_pending_and_complete(client, api_module):
    mem_dir = api_module.MEMORY_DIR
    output_dir = api_module.OUTPUT_DIR
    archive_dir = api_module.ARCHIVE_DIR
    mem_dir.mkdir(exist_ok=True)
    file = mem_dir / "data.json"
    file.write_text(json.dumps({"content": "info"}), encoding="utf-8")

    resp = client.get("/pending")
    assert resp.json()["files"] == ["data.json"]

    resp = client.get("/start_interview", params={"file": "data.json"})
    assert resp.json()["text"] == "info"

    profile = {"done": True}
    resp = client.post(
        "/complete_interview",
        json={"file": "data.json", "profile": profile},
    )
    assert resp.status_code == 200
    assert (output_dir / "data.json").exists()
    assert not file.exists()
    archived = [p for p in archive_dir.glob("data*.json")]
    assert archived

    resp = client.get("/pending")
    assert resp.json()["files"] == []


def test_start_interview_bad_memory_file(client, api_module):
    path = api_module.MEMORY_DIR / "bad.json"
    path.write_text("not-json", encoding="utf-8")

    resp = client.get("/start_interview", params={"file": "bad.json"})
    assert resp.status_code == 400
    assert "Invalid memory file" in resp.json()["detail"]


def test_create_app_respects_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    captured = {}

    class DummyInterviewer:
        def __init__(self, provider=None, **kwargs):
            captured["provider"] = provider

    monkeypatch.setattr("digital_persona.interview.PersonalityInterviewer", DummyInterviewer)
    import importlib
    import digital_persona.api as api
    api = importlib.reload(api)
    api.create_app()
    assert captured["provider"] == "ollama"


