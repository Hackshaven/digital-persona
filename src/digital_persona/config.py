import json
import os
from pathlib import Path

from dotenv import load_dotenv


def persona_dir() -> Path:
    base = os.getenv("PERSONA_DIR")
    if base:
        return Path(base)
    return Path(__file__).resolve().parents[2] / "persona"


CONFIG_FILE = persona_dir() / "persona_config.json"


def load_env() -> None:
    """Load environment variables from a .env file if present.

    Searches the current directory and the project root so scripts can be
    executed from any subdirectory during development.
    """
    root = persona_dir().parent
    candidates = [
        Path(".env"),
        Path(".devcontainer/.env"),
        root / ".env",
        root / ".devcontainer/.env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)
            break


# Load environment variables on import so other modules see them
load_env()


def load_config() -> dict:
    try:
        text = CONFIG_FILE.read_text()
        cfg = json.loads(text)
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        pass
    return {}


def enabled_services(default: list[str] | None = None) -> list[str]:
    env = os.getenv("ENABLED_SERVICES")
    if env:
        return [s.strip() for s in env.split(",") if s.strip()]
    cfg = load_config()
    if default is None:
        default = ["ingest", "mcp"]
    return cfg.get("enabled_services", default)
