import json
from pathlib import Path

from digital_persona.secure_storage import (
    get_fernet,
    save_json_encrypted,
    encrypt_bytes,
)
from digital_persona.decrypt import decrypt_persona


def test_decrypt_persona(tmp_path: Path):
    base = tmp_path / "persona"
    base.mkdir()
    fernet = get_fernet(base)

    data = {"foo": "bar"}
    save_json_encrypted(data, base / "profile.json", fernet)

    processed = base / "processed"
    processed.mkdir()
    encrypted = encrypt_bytes(b"hello", fernet)
    (processed / "note.txt").write_bytes(encrypted)

    out_dir = tmp_path / "out"
    decrypt_persona(base, out_dir)

    out = json.loads((out_dir / "profile.json").read_text())
    assert out == data
    assert (out_dir / "processed" / "note.txt").read_bytes() == b"hello"
