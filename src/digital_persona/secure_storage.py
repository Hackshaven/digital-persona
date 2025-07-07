import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

"""Helpers for encrypting persona data on disk.

The API creates a :class:`~cryptography.fernet.Fernet` instance via
``get_fernet`` and passes it to ``save_json_encrypted`` and
``load_json_encrypted`` whenever profile or memory files are written or
read.  A key can be supplied through the ``PERSONA_KEY`` environment
variable.  If that variable is unset, a new key is generated and stored
in ``<base_dir>/.persona.key`` so it persists across runs.
"""


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
            os.chmod(key_path, 0o600)  # Restrict file permissions to owner only
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


def encrypt_bytes(data: bytes, fernet: Fernet) -> bytes:
    """Return encrypted ``data`` using ``fernet``."""
    return fernet.encrypt(data)


def decrypt_bytes(data: bytes, fernet: Fernet) -> bytes:
    """Decrypt ``data`` if possible, otherwise return it unchanged."""
    try:
        return fernet.decrypt(data)
    except InvalidToken:
        return data
