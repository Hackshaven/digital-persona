"""Minimal FastAPI application exposing interview utilities."""

from __future__ import annotations

import os
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from importlib import resources
from werkzeug.utils import secure_filename
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
# where memory JSON files await the interview step
MEMORY_DIR = PERSONA_DIR / "memory"
INPUT_DIR = PERSONA_DIR / "input"
PROCESSED_DIR = PERSONA_DIR / "processed"
OUTPUT_DIR = PERSONA_DIR / "output"
ARCHIVE_DIR = PERSONA_DIR / "archive"
# web UI resources live in the ``frontend`` package
FRONTEND_DIR = resources.files("frontend")
FERNET = get_fernet(PERSONA_DIR)

PERSONA_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)


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
        return profile

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
        """Return a list of memory JSON files awaiting interview."""
        files = [p.name for p in MEMORY_DIR.glob("*.json") if p.is_file()]
        return {"files": sorted(files)}

    @app.get("/start_interview")
    def start_interview(file: str) -> dict:
        """Load a memory JSON file and return its ``content`` field."""
        sanitized_file = secure_filename(file)
        path = (MEMORY_DIR / sanitized_file).resolve()
        if not str(path).startswith(str(MEMORY_DIR)):
            raise HTTPException(status_code=400, detail="Invalid file path")
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        try:
            data = load_json_encrypted(path, FERNET)
        except json.JSONDecodeError:
            hint = "Invalid memory file; make sure you have run the ingest loop"
            raise HTTPException(status_code=400, detail=hint)
        text = data.get("content")
        if not isinstance(text, str):
            raise HTTPException(status_code=400, detail="Memory missing 'content' field")
        return {"text": text}

    @app.post("/complete_interview")
    def complete_interview(req: CompleteRequest) -> dict:
        """Save interview results and archive the memory file."""
        sanitized_file = secure_filename(req.file)
        mem_path = (MEMORY_DIR / sanitized_file).resolve()
        if not str(mem_path).startswith(str(MEMORY_DIR)):
            raise HTTPException(status_code=400, detail="Invalid file path")
        if not mem_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        out_path = (OUTPUT_DIR / (Path(sanitized_file).stem + ".json")).resolve()
        if not str(out_path).startswith(str(OUTPUT_DIR)):
            raise HTTPException(status_code=400, detail="Invalid file path")
        save_json_encrypted(req.profile, out_path, FERNET)
        archive = (ARCHIVE_DIR / sanitized_file).resolve()
        if not str(archive).startswith(str(ARCHIVE_DIR)):
            raise HTTPException(status_code=400, detail="Invalid file path")
        if archive.exists():
            safe_ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            archive = archive.with_name(f"{archive.stem}-{safe_ts}{archive.suffix}")
        shutil.move(str(mem_path), str(archive))
        return {"status": "saved"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        index_html = resources.files("frontend").joinpath("index.html")
        return index_html.read_text(encoding="utf-8")

    return app



