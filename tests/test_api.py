import json
import os
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

_BASE = TemporaryDirectory()
os.environ["PERSONA_DIR"] = _BASE.name

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
from digital_persona.api import create_app


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
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PERSONA_DIR", str(tmp_path))
    app = create_app(StubInterviewer())
    return TestClient(app)


def test_generate_questions_endpoint(client):
    resp = client.post("/generate_questions", json={"notes": "text"})
    assert resp.status_code == 200
    assert resp.json()["questions"] == ["Q1?", "Q2?"]


def test_profile_saved_and_loaded(client, tmp_path):
    qa = [{"question": "Q1", "answer": "A1"}]
    resp = client.post("/profile_from_answers", json={"notes": "txt", "qa": qa})
    assert resp.status_code == 200
    prof = resp.json()
    assert prof["traits"]["openness"] == 0.5

    resp2 = client.get("/profile/current")
    assert resp2.status_code == 200
    assert resp2.json()["traits"]["openness"] == 0.5


def test_memory_save_and_timeline(client, tmp_path):
    resp = client.post("/memory/save", json={"text": "note"})
    assert resp.status_code == 200
    ts = resp.json()["timestamp"]

    timeline = client.get("/memory/timeline").json()
    assert any(m["timestamp"] == ts for m in timeline)


def test_pending_and_complete(client, tmp_path):
    from digital_persona.api import INPUT_DIR, PROCESSED_DIR, OUTPUT_DIR
    input_dir = INPUT_DIR
    input_dir.mkdir(exist_ok=True)
    file = input_dir / "data.txt"
    file.write_text("info", encoding="utf-8")

    resp = client.get("/pending")
    assert resp.json()["files"] == ["data.txt"]

    resp = client.get("/start_interview", params={"file": "data.txt"})
    assert resp.json()["text"] == "info"

    profile = {"done": True}
    resp = client.post(
        "/complete_interview",
        json={"file": "data.txt", "profile": profile},
    )
    assert resp.status_code == 200
    assert (PROCESSED_DIR / "data.txt").exists()
    assert (OUTPUT_DIR / "data.json").exists()


