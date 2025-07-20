import json
import os
import logging
from datetime import datetime, timedelta, UTC
import asyncio
import httpx
from fastapi import APIRouter, FastAPI, Security, Request
from fastapi.security import APIKeyQuery
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from digital_persona.utils.filename import sanitize_filename
from digital_persona.secure_storage import (
    get_fernet,
    save_json_encrypted,
    load_json_encrypted,
)

from digital_persona import config as dp_config

dp_config.load_env()
from digital_persona.ingest import INPUT_DIR, PROCESSED_DIR, _persona_dir

FERNET = get_fernet(_persona_dir())

STATE_FILE = _persona_dir() / "limitless_state.json"
API_URL = os.getenv("LIMITLESS_API_URL", "https://api.limitless.ai/v1")
API_KEY = os.getenv("LIMITLESS_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "LIMITLESS_API_KEY environment variable is required to use Limitless ingest"
    )
POLL_INTERVAL = float(os.getenv("LIMITLESS_POLL_INTERVAL", "300"))
LOOKBACK_DAYS = int(os.getenv("LIMITLESS_LOOKBACK_DAYS", "2"))

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

router = APIRouter()

api_key_query = APIKeyQuery(name="api_key", auto_error=False)


class LifelogParams(BaseModel):
    """Parameters accepted by the lifelogs endpoint."""

    start: str | None = Field(
        default=None,
        description="ISO 8601 start timestamp",
        examples=["2025-07-19T00:00:00Z"],
    )
    end: str | None = Field(
        default=None,
        description="ISO 8601 end timestamp",
        examples=["2025-07-20T00:00:00Z"],
    )
    keyword: str | None = Field(
        default=None,
        description="Filter entries containing this text",
        examples=["meeting"],
    )
    speaker_name: str | None = Field(
        default=None,
        alias="speakerName",
        description="Filter entries attributed to this speaker",
        examples=["Alice"],
    )

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


def setup(app: FastAPI) -> None:
    """Attach background ingest task to *app* startup."""

    async def _loop() -> None:
        logger.info("Starting Limitless ingest loop (interval=%s)", POLL_INTERVAL)
        while True:
            run_once()
            await asyncio.sleep(POLL_INTERVAL)

    app.add_event_handler("startup", lambda: asyncio.create_task(_loop()))

    @app.get("/.well-known/ai-plugin.json", include_in_schema=False)
    def ai_plugin(request: Request) -> JSONResponse:
        """Return Open WebUI plugin manifest."""
        base = str(request.base_url).rstrip("/")
        manifest = {
            "schema_version": "v1",
            "name_for_human": "Limitless MCP",
            "name_for_model": "limitless_mcp",
            "description_for_human": "Search your stored Limitless lifelogs",
            "description_for_model": "Search previously ingested lifelogs via the MCP server",
            "auth": {"type": "none"},
            "api": {
                "type": "openapi",
                "url": f"{base}{app.openapi_url}",
                "is_user_authenticated": False,
            },
            "logo_url": f"{base}/logo.png",
            "contact_email": "support@example.com",
            "legal_info_url": "https://example.com/legal",
        }
        return JSONResponse(content=manifest)


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def _fetch_entries(
    *, start: str | None = None, cursor: str | None = None, api_key: str = API_KEY
) -> tuple[list[dict], str | None]:
    """Return lifelog entries and the next cursor."""

    headers = {"X-API-Key": api_key}
    params = {}
    if start:
        params["start"] = start
    if cursor:
        params["cursor"] = cursor
    url = f"{API_URL.rstrip('/')}/lifelogs"
    resp = httpx.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    items: list[dict]
    next_cursor: str | None = None
    if isinstance(data, dict):
        items = data.get("data", {}).get("lifelogs") or data.get("items", [])
        next_cursor = data.get("meta", {}).get("lifelogs", {}).get("nextCursor")
    else:
        items = data
    return items, next_cursor


def _save_entry(entry: dict) -> None:
    entry_id = entry.get("id") or entry.get("uuid") or entry.get("timestamp")
    if not entry_id:
        entry_id = datetime.now(UTC).timestamp()
    entry_id = sanitize_filename(str(entry_id))
    out = _get_entry_filename(entry_id)
    obj = {k: v for k, v in entry.items()}
    save_json_encrypted(obj, out, FERNET)
    logger.info("Saved %s", out.name)


def _get_entry_filename(entry_id: str) -> os.PathLike:
    """Construct the file path for a given entry ID."""
    return INPUT_DIR / f"limitless-{entry_id}.json"


def _contains_speaker(obj: object, speaker_name: str) -> bool:
    """Return True if *obj* or nested values contain the speaker name."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"speakerName", "speaker"}:
                if value and speaker_name.lower() in str(value).lower():
                    return True
            if key == "metadata" and isinstance(value, dict):
                val = value.get("speakerName") or value.get("speaker")
                if val and speaker_name.lower() in str(val).lower():
                    return True
            if _contains_speaker(value, speaker_name):
                return True
    elif isinstance(obj, list):
        return any(_contains_speaker(v, speaker_name) for v in obj)
    return False


def _search_local_entries(
    *,
    start: str | None = None,
    end: str | None = None,
    keyword: str | None = None,
    speaker_name: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return stored Limitless entries from the persona directory."""

    files = sorted(
        list(PROCESSED_DIR.glob("limitless-*.json"))
        + list(INPUT_DIR.glob("limitless-*.json"))
    )
    start_dt = None
    end_dt = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except Exception:
            start_dt = None
    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except Exception:
            end_dt = None

    items: list[dict] = []
    for path in files:
        try:
            obj = load_json_encrypted(path, FERNET)
        except Exception:
            continue
        ts = obj.get("updatedAt") or obj.get("timestamp") or obj.get("endTime")
        if ts:
            try:
                ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if start_dt and ts_dt < start_dt:
                    continue
                if end_dt and ts_dt > end_dt:
                    continue
            except Exception:
                pass
        if keyword:
            text = json.dumps(obj, ensure_ascii=False).lower()
            if keyword.lower() not in text:
                continue
        if speaker_name:
            try:
                if not _contains_speaker(obj, speaker_name):
                    continue
            except Exception:
                continue
        items.append(obj)
        if len(items) >= limit:
            break
    return items


def run_once() -> None:
    state = _load_state()
    last_id: str | None = state.get("last_id")
    cursor: str | None = state.get("cursor")
    start: str | None = state.get("start")

    if last_id and not _get_entry_filename(last_id).exists():
        last_id = None

    if not cursor and not start:
        start = (
            (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS))
            .isoformat()
            .replace("+00:00", "Z")
        )

    try:
        entries, next_cursor = _fetch_entries(start=start, cursor=cursor)
    except Exception:
        logger.exception("Failed to fetch entries")
        return
    latest_ts = None
    latest_id = last_id
    for e in entries:
        _save_entry(e)
        ts = e.get("updatedAt") or e.get("timestamp") or e.get("endTime")
        if ts and (latest_ts is None or ts > latest_ts):
            latest_ts = ts
        eid = e.get("id") or e.get("uuid") or e.get("timestamp")
        if eid:
            latest_id = eid
    if latest_ts:
        state["start"] = latest_ts
    elif start:
        state["start"] = start
    if latest_id:
        state["last_id"] = latest_id
    if next_cursor:
        state["cursor"] = next_cursor
    else:
        state.pop("cursor", None)
    _save_state(state)


@router.post(
    "/lifelogs",
    name="limitless_lifelogs",
    description="Fetch Limitless lifelog entries",
    operation_id="limitless_lifelogs",
)
async def api_lifelogs(
    params: LifelogParams | None = None,
    api_key: str | None = Security(api_key_query),
) -> dict:
    """Return Limitless entries via the MCP server."""
    start = params.start if params else None
    end = params.end if params else None
    keyword = params.keyword if params else None
    speaker_name = params.speaker_name if params else None
    # OpenAPI tooling may send literal "string" when no value is provided
    if start == "string":
        start = None
    if end == "string":
        end = None
    if keyword == "string":
        keyword = None
    if speaker_name == "string":
        speaker_name = None
    items = _search_local_entries(
        start=start, end=end, keyword=keyword, speaker_name=speaker_name
    )
    return {"items": items}


def _cli() -> None:
    """Run the ingest loop as a standalone service."""

    async def main() -> None:
        logger.info("Starting Limitless ingest loop (interval=%s)", POLL_INTERVAL)
        while True:
            run_once()
            await asyncio.sleep(POLL_INTERVAL)

    asyncio.run(main())


if __name__ == "__main__":
    _cli()
