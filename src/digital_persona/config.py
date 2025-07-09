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
    """Load environment variables from a .env file if present."""
    for name in (".env", ".devcontainer/.env"):
        path = Path(name)
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
