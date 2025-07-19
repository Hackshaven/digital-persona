import json
import os
import logging
from datetime import datetime, timedelta, UTC
import asyncio
import httpx
from fastapi import APIRouter, FastAPI

from digital_persona import config as dp_config

dp_config.load_env()
from digital_persona.ingest import INPUT_DIR, _persona_dir

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


def setup(app: FastAPI) -> None:
    """Attach background ingest task to *app* startup."""

    async def _loop() -> None:
        logger.info("Starting Limitless ingest loop (interval=%s)", POLL_INTERVAL)
        while True:
            run_once()
            await asyncio.sleep(POLL_INTERVAL)

    app.add_event_handler("startup", lambda: asyncio.create_task(_loop()))


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def _fetch_entries(*, start: str | None = None, cursor: str | None = None) -> tuple[list[dict], str | None]:
    """Return lifelog entries and the next cursor."""

    headers = {"X-API-Key": API_KEY}
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
    entry_id = str(entry_id).replace(".", "")  # Remove decimal point if present
    out = INPUT_DIR / f"limitless-{entry_id}.json"
    obj = {k: v for k, v in entry.items()}
    out.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %s", out.name)


def run_once() -> None:
    state = _load_state()
    last_id: str | None = state.get("last_id")
    cursor: str | None = state.get("cursor")
    start: str | None = state.get("start")

    if last_id and not (INPUT_DIR / f"limitless-{last_id}.json").exists():
        last_id = None

    if not cursor and not start:
        start = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).isoformat().replace("+00:00", "Z")

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


@router.get("/lifelogs")
async def api_lifelogs(start: str | None = None, cursor: str | None = None) -> dict:
    """Return Limitless entries via the MCP server."""
    items, next_cursor = _fetch_entries(start=start, cursor=cursor)
    return {"items": items, "next_cursor": next_cursor}


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
