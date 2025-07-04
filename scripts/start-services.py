#!/usr/bin/env python3
"""Start the API server and ingest loop."""
import subprocess
import signal
import sys
from pathlib import Path

processes = []

LOG_DIR = Path("/tmp")
UVICORN_LOG = LOG_DIR / "uvicorn.log"
INGEST_LOG = LOG_DIR / "ingest.log"


def launch(cmd, log_path):
    log_file = open(log_path, "a")
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    processes.append((proc, log_file))


def shutdown(*_):
    for proc, log_file in processes:
        proc.terminate()
    for proc, log_file in processes:
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        log_file.close()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

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

# Wait for subprocesses
for proc, _ in processes:
    proc.wait()
