from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Dict, Any
import subprocess
import shutil
import tempfile
import logging


def _ollama_client():
    """Return an Ollama client respecting OLLAMA_BASE_URL/OLLAMA_HOST."""
    host = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST")
    if host:
        import ollama
        return ollama.Client(host=host)
    import ollama
    return ollama

try:
    from mutagen import File as MutagenFile
except Exception:  # pragma: no cover - optional dependency may be missing
    MutagenFile = None  # type: ignore

try:
    from PIL import Image, ExifTags
except Exception:  # pragma: no cover - optional dependency may be missing
    Image = None  # type: ignore
    ExifTags = None  # type: ignore


def _persona_dir() -> Path:
    base = os.getenv("PERSONA_DIR")
    if base:
        return Path(base)
    return Path(__file__).resolve().parents[2] / "persona"


PERSONA_DIR = _persona_dir()
INPUT_DIR = PERSONA_DIR / "input"
PROCESSED_DIR = PERSONA_DIR / "processed"
MEMORY_DIR = PERSONA_DIR / "memory"
TROUBLE_DIR = PERSONA_DIR / "troubleshooting"

for d in (PERSONA_DIR, INPUT_DIR, PROCESSED_DIR, MEMORY_DIR, TROUBLE_DIR):
    d.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# Patterns that should be sanitized from user inputs
_SANITIZE_PATTERNS: Iterable[re.Pattern[str]] = [
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
]

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi"}

# prompt used for LLM image captioning
CAPTION_PROMPT = "Describe the image in one concise sentence."
SUMMARY_PROMPT = "Summarize the audio transcript in one short paragraph."
SENTIMENT_PROMPT = (
    "Classify the sentiment of the following text as positive, negative, or neutral."
)


def _sanitize(text: str) -> str:
    for pat in _SANITIZE_PATTERNS:
        text = pat.sub("[removed]", text)
    return text


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def _is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_SUFFIXES


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def _extract_exif(path: Path) -> Dict[str, Any]:
    """Return basic EXIF metadata for an image file."""
    meta: Dict[str, Any] = {}
    if Image is None:
        return meta
    try:
        with Image.open(path) as img:
            info = img.getexif()
            if not info:
                return meta
            exif = {
                ExifTags.TAGS.get(k, k): v for k, v in info.items() if k in ExifTags.TAGS
            }
            if "DateTimeOriginal" in exif:
                meta["originalTimestamp"] = exif["DateTimeOriginal"]
            gps = exif.get("GPSInfo")
            if gps:
                gps_data = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}

                def _to_deg(value):
                    d, m, s = value
                    return d[0] / d[1] + m[0] / m[1] / 60 + s[0] / s[1] / 3600

                if {
                    "GPSLatitude",
                    "GPSLatitudeRef",
                    "GPSLongitude",
                    "GPSLongitudeRef",
                } <= gps_data.keys():
                    lat = _to_deg(gps_data["GPSLatitude"])
                    if gps_data["GPSLatitudeRef"] != "N":
                        lat = -lat
                    lon = _to_deg(gps_data["GPSLongitude"])
                    if gps_data["GPSLongitudeRef"] != "E":
                        lon = -lon
                    meta["latitude"] = lat
                    meta["longitude"] = lon
    except Exception:
        pass
    return meta


def _extract_audio_metadata(path: Path) -> Dict[str, Any]:
    """Return duration and other basic metadata for an audio file."""
    meta: Dict[str, Any] = {}
    if MutagenFile is None:
        return meta
    try:
        audio = MutagenFile(path)
        if audio and audio.info:
            meta["duration"] = getattr(audio.info, "length", None)
            meta["sampleRate"] = getattr(audio.info, "sample_rate", None)
            meta["channels"] = getattr(audio.info, "channels", None)
    except Exception:
        pass
    return meta


def _extract_video_metadata(path: Path) -> Dict[str, Any]:
    """Return duration and basic metadata for a video file."""
    meta: Dict[str, Any] = {}
    if not shutil.which("ffprobe"):
        return meta
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,duration",
            "-of",
            "json",
            str(path),
        ]
        out = subprocess.check_output(cmd)
        data = json.loads(out)
        stream = (data.get("streams") or [{}])[0]
        if stream.get("duration"):
            meta["duration"] = float(stream["duration"])
        if stream.get("width") and stream.get("height"):
            meta["resolution"] = f"{stream['width']}x{stream['height']}"
        fr = stream.get("avg_frame_rate")
        if fr and "/" in fr:
            num, den = fr.split("/")
            try:
                meta["frameRate"] = float(num) / float(den)
            except Exception:
                pass
    except Exception:
        pass
    return meta


def _extract_frame(path: Path) -> Path | None:
    """Return path to a temporary JPEG frame from ``path``."""
    if not shutil.which("ffmpeg"):
        return None
    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(temp_fd)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-frames:v",
                "1",
                temp_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return Path(temp_path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        return None


def _extract_video_audio(path: Path) -> Path | None:
    """Extract audio from ``path`` and return temporary WAV file path."""
    if not shutil.which("ffmpeg"):
        return None
    temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
    os.close(temp_fd)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                temp_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return Path(temp_path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        return None


def _transcribe_audio(path: Path) -> str:
    """Return a transcript for ``path`` using an LLM if available."""
    provider = os.getenv("TRANSCRIBE_PROVIDER", "openai").lower()
    model = os.getenv("TRANSCRIBE_MODEL")

    logger.debug("Transcribing %s via %s", path.name, provider)

    if provider == "openai":
        model = model or "whisper-1"
        try:
            import openai

            with open(path, "rb") as f:
                resp = openai.audio.transcriptions.create(model=model, file=f)
            text = resp.text if hasattr(resp, "text") else resp["text"]
            return text.strip()
        except Exception as exc:
            logger.exception("OpenAI transcription failed for %s", path.name)
            return ""

    if provider == "whisper":
        try:
            import whisper

            wmodel = whisper.load_model(model or "base")
            result = wmodel.transcribe(str(path))
            return result.get("text", "").strip()
        except Exception:
            logger.exception("Whisper transcription failed for %s", path.name)
            return ""

    logger.warning("Unknown transcription provider %s", provider)
    return ""


def _generate_caption(path: Path) -> str:
    """Return a short caption for ``path`` using an LLM if available."""
    provider = os.getenv("CAPTION_PROVIDER", "ollama").lower()
    model = os.getenv("CAPTION_MODEL")

    logger.debug("Captioning %s via %s", path.name, provider)

    if provider == "openai":
        model = model or "gpt-4o"
        try:
            import openai

            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CAPTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ]
            resp = openai.chat.completions.create(model=model, messages=messages)
            return resp.choices[0].message.content.strip()
        except Exception:
            logger.exception("OpenAI captioning failed for %s", path.name)
            return ""

    if provider == "ollama":
        model = model or os.getenv("OLLAMA_MODEL", "llava")
        try:
            client = _ollama_client()

            with open(path, "rb") as f:
                img_bytes = f.read()
            resp = client.generate(model=model, prompt=CAPTION_PROMPT, images=[img_bytes])
            return (resp["response"] if isinstance(resp, dict) else resp.response).strip()
        except Exception:
            logger.exception("Ollama captioning failed for %s", path.name)
            return ""

    logger.warning("Unknown caption provider %s", provider)
    return ""


def _generate_summary(text: str) -> str:
    """Return a short summary for ``text`` using an LLM if available."""
    provider = os.getenv("CAPTION_PROVIDER", "ollama").lower()
    model = os.getenv("CAPTION_MODEL")

    if not text:
        return ""

    logger.debug("Summarizing text via %s", provider)

    def _via_openai() -> str:
        mdl = model or "gpt-4o"
        try:
            import openai

            messages = [
                {"role": "user", "content": f"{SUMMARY_PROMPT}\n{text}"},
            ]
            resp = openai.chat.completions.create(model=mdl, messages=messages)
            return resp.choices[0].message.content.strip()
        except Exception:
            logger.exception("OpenAI summary failed")
            return ""

    if provider == "openai":
        return _via_openai()

    if provider == "ollama":
        model = model or os.getenv("OLLAMA_MODEL", "llama3")
        try:
            client = _ollama_client()

            resp = client.generate(model=model, prompt=f"{SUMMARY_PROMPT}\n{text}")
            return (resp["response"] if isinstance(resp, dict) else resp.response).strip()
        except Exception:
            logger.exception("Ollama summary failed")
            if os.getenv("OPENAI_API_KEY"):
                logger.info("Falling back to OpenAI for summary")
                return _via_openai()
            return ""

    logger.warning("Unknown caption provider %s", provider)
    return ""


def _analyze_sentiment(text: str) -> str:
    """Return a simple sentiment classification."""
    provider = os.getenv("CAPTION_PROVIDER", "ollama").lower()
    model = os.getenv("CAPTION_MODEL")

    if not text:
        return ""

    logger.debug("Analyzing sentiment via %s", provider)

    def _via_openai() -> str:
        mdl = model or "gpt-4o"
        try:
            import openai

            messages = [
                {"role": "user", "content": f"{SENTIMENT_PROMPT}\n{text}"},
            ]
            resp = openai.chat.completions.create(model=mdl, messages=messages)
            return resp.choices[0].message.content.strip().split()[0].lower()
        except Exception:
            logger.exception("OpenAI sentiment analysis failed")
            return ""

    if provider == "openai":
        return _via_openai()

    if provider == "ollama":
        model = model or os.getenv("OLLAMA_MODEL", "llama3")
        try:
            client = _ollama_client()

            resp = client.generate(model=model, prompt=f"{SENTIMENT_PROMPT}\n{text}")
            content = resp["response"] if isinstance(resp, dict) else resp.response
            return content.strip().split()[0].lower()
        except Exception:
            logger.exception("Ollama sentiment analysis failed")
            if os.getenv("OPENAI_API_KEY"):
                logger.info("Falling back to OpenAI for sentiment analysis")
                return _via_openai()
            return ""

    logger.warning("Unknown caption provider %s", provider)
    return ""


def preprocess_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        text = _strip_html(text)
    elif suffix == ".json":
        try:
            obj = json.loads(text)
            text = json.dumps(obj, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return _sanitize(text).strip()


def process_file(path: Path) -> bool:
    """Process ``path`` and return True on success."""
    logger.info("Processing %s", path.name)
    now = datetime.now(timezone.utc)
    ts = now.isoformat()
    safe_ts = now.strftime("%Y%m%d%H%M%S%f")
    mem_path = MEMORY_DIR / f"{safe_ts}.json"

    # determine final destination for the original file
    dest = PROCESSED_DIR / path.name
    if dest.exists():
        dest = dest.with_name(f"{dest.stem}-{safe_ts}{dest.suffix}")

    try:
        if _is_image(path):
            caption = _generate_caption(path)
            if not caption:
                raise RuntimeError("caption failed")
            meta = _extract_exif(path)
            mem_obj = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Image",
            "name": path.name,
            "content": caption,
            "caption": caption,
            "metadata": meta,
            "timestamp": ts,
            "source": str(dest.relative_to(PERSONA_DIR)),
        }
        elif _is_audio(path):
            transcript = _transcribe_audio(path)
            if not transcript:
                raise RuntimeError("transcription failed")
            summary = _generate_summary(transcript)
            sentiment = _analyze_sentiment(transcript)
            meta = _extract_audio_metadata(path)
            mem_obj = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Audio",
            "name": path.name,
            "content": summary or transcript,
            "transcript": transcript,
            "summary": summary,
            "sentiment": sentiment,
            "metadata": meta,
            "timestamp": ts,
            "source": str(dest.relative_to(PERSONA_DIR)),
        }
        elif _is_video(path):
            frame_path = _extract_frame(path)
            caption = _generate_caption(frame_path) if frame_path else ""
            if frame_path:
                frame_path.unlink(missing_ok=True)
            audio_path = _extract_video_audio(path)
            transcript = _transcribe_audio(audio_path) if audio_path else ""
            if audio_path:
                audio_path.unlink(missing_ok=True)
            if not caption and not transcript:
                raise RuntimeError("video analysis failed")
            summary = _generate_summary(transcript)
            sentiment = _analyze_sentiment(transcript)
            meta = _extract_video_metadata(path)
            mem_obj = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Video",
            "name": path.name,
            "content": summary or caption,
            "caption": caption,
            "transcript": transcript,
            "summary": summary,
            "sentiment": sentiment,
            "metadata": meta,
            "timestamp": ts,
            "source": str(dest.relative_to(PERSONA_DIR)),
        }
        else:
            content = preprocess_text(path)
            mem_obj = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Note",
            "name": path.name,
            "content": content,
            "timestamp": ts,
            "source": str(dest.relative_to(PERSONA_DIR)),
        }

        with open(mem_path, "w", encoding="utf-8") as f:
            json.dump(mem_obj, f)
        shutil.move(str(path), str(dest))
        logger.info("Saved memory %s", mem_path.name)
        return True
    except Exception as exc:
        logger.exception("Failed to process %s", path.name)
        fail = TROUBLE_DIR / path.name
        if fail.exists():
            fail = fail.with_name(f"{fail.stem}-{safe_ts}{fail.suffix}")
        shutil.move(str(path), str(fail))
        logger.info("Moved %s to %s", path.name, fail)
        return False


def process_pending_files() -> None:
    files = [p for p in INPUT_DIR.iterdir() if p.is_file()]
    if not files:
        logger.debug("No files to process")
    for p in files:
        process_file(p)


__all__ = ["process_pending_files"]


def _cli() -> None:
    import time
    interval = float(os.getenv("INGEST_INTERVAL", "5"))
    logger.info("Starting ingest loop (interval=%s seconds)", interval)
    while True:
        process_pending_files()
        time.sleep(interval)


if __name__ == "__main__":
    _cli()
