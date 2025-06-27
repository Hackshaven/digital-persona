"""Minimal FastAPI application exposing interview utilities."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from importlib import resources
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .interview import PersonalityInterviewer
from .secure_storage import (
    get_fernet,
    save_json_encrypted,
    load_json_encrypted,
)


def _valid_openai_key() -> bool:
    """Return True if OPENAI_API_KEY looks like a real key."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return False
    if key.strip().startswith("${{"):
        return False
    return True


def _persona_dir() -> Path:
    """Return the base directory for stored profiles and memories."""
    base = os.getenv("PERSONA_DIR")
    if base:
        return Path(base)
    return Path(__file__).resolve().parents[2] / "persona"


PERSONA_DIR = _persona_dir()
PROFILE_FILE = PERSONA_DIR / "profile.json"
MEMORY_DIR = PERSONA_DIR / "memory"
INPUT_DIR = PERSONA_DIR / "input"
PROCESSED_DIR = PERSONA_DIR / "processed"
OUTPUT_DIR = PERSONA_DIR / "output"
# web UI resources live in the ``frontend`` package
FRONTEND_DIR = resources.files("frontend")
FERNET = get_fernet(PERSONA_DIR)

PERSONA_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


class Notes(BaseModel):
    notes: str


class QAItem(BaseModel):
    question: str
    answer: str


class QAPayload(BaseModel):
    notes: str
    qa: List[QAItem]


class FollowupRequest(BaseModel):
    question: str
    answer: str


class MemoryItem(BaseModel):
    text: str
    timestamp: Optional[str] = None


class CompleteRequest(BaseModel):
    file: str
    profile: dict


def create_app(interviewer: PersonalityInterviewer | None = None) -> FastAPI:
    if interviewer is None:
        provider = "openai" if _valid_openai_key() else "ollama"
        interviewer = PersonalityInterviewer(provider=provider)
    app = FastAPI()
    # StaticFiles requires an actual filesystem path
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.post("/generate_questions")
    def generate_questions(payload: Notes) -> dict:
        qs = interviewer.generate_questions(payload.notes)
        return {"questions": qs}

    @app.post("/generate_followup")
    def generate_followup(payload: FollowupRequest) -> dict:
        follow = interviewer.generate_followup(payload.question, payload.answer)
        return {"followup": follow}

    @app.post("/profile_from_answers")
    def profile_from_answers(payload: QAPayload) -> dict:
        qa_pairs = [f"Q: {item.question}\nA: {item.answer}" for item in payload.qa]
        profile = interviewer.profile_from_answers(payload.notes, qa_pairs)
        save_json_encrypted(profile, PROFILE_FILE, FERNET)
        return profile

    @app.get("/profile/current")
    def profile_current() -> dict:
        if not PROFILE_FILE.exists():
            raise HTTPException(status_code=404, detail="No profile saved")
        return load_json_encrypted(PROFILE_FILE, FERNET)

    @app.post("/memory/save")
    def memory_save(item: MemoryItem) -> dict:
        ts = item.timestamp or datetime.now(timezone.utc).isoformat()
        safe_ts = ts.replace(":", "-")
        path = MEMORY_DIR / f"{safe_ts}.json"
        save_json_encrypted({"text": item.text, "timestamp": ts}, path, FERNET)
        return {"status": "saved", "timestamp": ts}

    @app.get("/memory/timeline")
    def memory_timeline() -> List[dict]:
        memories = []
        for p in sorted(MEMORY_DIR.glob("*.json")):
            memories.append(load_json_encrypted(p, FERNET))
        memories.sort(key=lambda m: m.get("timestamp", ""))
        return memories

    @app.post("/tag_text_with_traits")
    def tag_text_with_traits(payload: Notes) -> dict:
        # Simple heuristic: return traits mentioned in the text
        trait_names = interviewer.trait_names
        text = payload.notes.lower()
        tags = [t for t in trait_names if t.lower() in text]
        return {"traits": tags}

    @app.get("/pending")
    def pending() -> dict:
        files = [p.name for p in INPUT_DIR.glob("*") if p.is_file()]
        return {"files": sorted(files)}

    @app.get("/start_interview")
    def start_interview(file: str) -> dict:
        path = INPUT_DIR / file
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return {"text": path.read_text(encoding="utf-8")}

    @app.post("/complete_interview")
    def complete_interview(req: CompleteRequest) -> dict:
        in_path = INPUT_DIR / req.file
        if not in_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        processed_path = PROCESSED_DIR / req.file
        if processed_path.exists():
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            processed_path = processed_path.with_stem(
                f"{processed_path.stem}-{ts}"
            )
        out_path = OUTPUT_DIR / (Path(req.file).stem + ".json")
        in_path.rename(processed_path)
        save_json_encrypted(req.profile, out_path, FERNET)
        return {"status": "saved"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        index_html = resources.files("frontend").joinpath("index.html")
        return index_html.read_text(encoding="utf-8")

    return app



