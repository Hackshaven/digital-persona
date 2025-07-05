"""Minimal FastAPI application exposing interview utilities."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from importlib import resources
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .interview import PersonalityInterviewer


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
# where memory JSON files await the interview step
MEMORY_DIR = PERSONA_DIR / "memory"
INPUT_DIR = PERSONA_DIR / "input"
PROCESSED_DIR = PERSONA_DIR / "processed"
OUTPUT_DIR = PERSONA_DIR / "output"
ARCHIVE_DIR = PERSONA_DIR / "archive"
# web UI resources live in the ``frontend`` package
FRONTEND_DIR = resources.files("frontend")

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
        PROFILE_FILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return profile

    @app.get("/profile/current")
    def profile_current() -> dict:
        if not PROFILE_FILE.exists():
            raise HTTPException(status_code=404, detail="No profile saved")
        with open(PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)

    @app.post("/memory/save")
    def memory_save(item: MemoryItem) -> dict:
        ts = item.timestamp or datetime.now(timezone.utc).isoformat()
        safe_ts = ts.replace(":", "-")
        path = MEMORY_DIR / f"{safe_ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"text": item.text, "timestamp": ts}, f)
        return {"status": "saved", "timestamp": ts}

    @app.get("/memory/timeline")
    def memory_timeline() -> List[dict]:
        memories = []
        for p in sorted(MEMORY_DIR.glob("*.json")):
            with open(p, encoding="utf-8") as f:
                memories.append(json.load(f))
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
        path = MEMORY_DIR / file
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
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
        mem_path = MEMORY_DIR / req.file
        if not mem_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        out_path = (OUTPUT_DIR / (Path(req.file).stem + ".json")).resolve()
        if not str(out_path).startswith(str(OUTPUT_DIR)):
            raise HTTPException(status_code=400, detail="Invalid file path")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(req.profile, f, indent=2)
        archive = ARCHIVE_DIR / req.file
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



