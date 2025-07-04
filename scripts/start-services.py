#!/usr/bin/env python3
"""Start the API server and ingest loop in the background."""

import subprocess
from pathlib import Path


LOG_DIR = Path("/tmp")
UVICORN_LOG = LOG_DIR / "uvicorn.log"
INGEST_LOG = LOG_DIR / "ingest.log"


def launch(cmd: list[str], log_path: Path) -> None:
    """Run *cmd* detached with output appended to *log_path*."""
    with open(log_path, "a") as log_file:
        subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def main() -> None:
    launch(
        [
            "poetry",
            "run",
            "uvicorn",
            "digital_persona.api:create_app",
            "--factory",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        UVICORN_LOG,
    )

    launch(["poetry", "run", "digital-persona-ingest"], INGEST_LOG)


if __name__ == "__main__":
    main()
