from pathlib import Path

from digital_persona.secure_storage import (
    get_fernet,
    encrypt_bytes,
)
from digital_persona.decrypt import decrypt_persona


def test_decrypt_persona(tmp_path: Path):
    base = tmp_path / "persona"
    base.mkdir()
    fernet = get_fernet(base)

    processed = base / "processed"
    processed.mkdir()
    encrypted = encrypt_bytes(b"hello", fernet)
    (processed / "note.txt").write_bytes(encrypted)

    out_dir = tmp_path / "out"
    decrypt_persona(base, out_dir)

    assert (out_dir / "processed" / "note.txt").read_bytes() == b"hello"


def test_decrypt_persona_binary_file(tmp_path: Path):
    base = tmp_path / "persona"
    base.mkdir()
    fernet = get_fernet(base)

    processed = base / "processed"
    processed.mkdir()
    # Simulate binary content (e.g., a small PNG header)
    original_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    encrypted = encrypt_bytes(original_bytes, fernet)
    (processed / "image.png").write_bytes(encrypted)

    out_dir = tmp_path / "out"
    decrypt_persona(base, out_dir)

    assert (out_dir / "processed" / "image.png").read_bytes() == original_bytes
