import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def get_fernet(base_dir: Path) -> Fernet:
    """Return a Fernet instance using a key from env or ``base_dir``."""
    key_env = os.getenv("PERSONA_KEY")
    key_path = base_dir / ".persona.key"
    if key_env:
        key = key_env.encode()
    else:
        if key_path.exists():
            key = key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
    return Fernet(key)


def save_json_encrypted(data: dict, path: Path, fernet: Fernet) -> None:
    """Encrypt ``data`` as JSON and write to ``path``."""
    token = fernet.encrypt(json.dumps(data).encode("utf-8"))
    path.write_bytes(token)


def load_json_encrypted(path: Path, fernet: Fernet) -> dict:
    """Load and decrypt JSON from ``path``.

    Falls back to plain JSON if decryption fails (for backward compatibility).
    """
    raw = path.read_bytes()
    try:
        decrypted = fernet.decrypt(raw)
        return json.loads(decrypted.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError):
        return json.loads(raw.decode("utf-8"))
