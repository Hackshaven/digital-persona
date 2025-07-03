import json
import os
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

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


def test_profile_saved_and_loaded(client):
    qa = [{"question": "Q1", "answer": "A1"}]
    resp = client.post("/profile_from_answers", json={"notes": "txt", "qa": qa})
    assert resp.status_code == 200
    prof = resp.json()
    assert prof["traits"]["openness"] == 0.5

    resp2 = client.get("/profile/current")
    assert resp2.status_code == 200
    assert resp2.json()["traits"]["openness"] == 0.5


def test_memory_save_and_timeline(client):
    resp = client.post("/memory/save", json={"text": "note"})
    assert resp.status_code == 200
    ts = resp.json()["timestamp"]

    timeline = client.get("/memory/timeline").json()
    assert any(m["timestamp"] == ts for m in timeline)


def test_pending_and_complete(client, api_module):
    mem_dir = api_module.MEMORY_DIR
    output_dir = api_module.OUTPUT_DIR
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


def test_start_interview_bad_memory_file(client, api_module):
    path = api_module.MEMORY_DIR / "bad.json"
    path.write_text("not-json", encoding="utf-8")

    resp = client.get("/start_interview", params={"file": "bad.json"})
    assert resp.status_code == 400
    assert "Invalid memory file" in resp.json()["detail"]


