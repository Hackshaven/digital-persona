import json
import os
from argparse import ArgumentParser
from pathlib import Path

from .secure_storage import get_fernet, load_json_encrypted


def decrypt_persona(base_dir: Path, out_dir: Path) -> None:
    """Decrypt all JSON files from *base_dir* into *out_dir*."""
    fernet = get_fernet(base_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in ("profile.json",):
        src = base_dir / name
        if src.exists():
            data = load_json_encrypted(src, fernet)
            (out_dir / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    for sub in ("memory", "output", "archive"):
        src_dir = base_dir / sub
        dest_dir = out_dir / sub
        if not src_dir.exists():
            continue
        dest_dir.mkdir(exist_ok=True)
        for path in src_dir.glob("*.json"):
            data = load_json_encrypted(path, fernet)
            (dest_dir / path.name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _cli() -> None:
    parser = ArgumentParser(description="Decrypt persona data to a folder")
    parser.add_argument("out", type=Path, help="Destination folder for decrypted JSON")
    parser.add_argument(
        "--persona-dir",
        type=Path,
        default=os.getenv("PERSONA_DIR", Path(__file__).resolve().parents[2] / "persona"),
        help="Base persona directory (default: env PERSONA_DIR or ./persona)",
    )
    args = parser.parse_args()
    decrypt_persona(args.persona_dir, args.out)


if __name__ == "__main__":
    _cli()
