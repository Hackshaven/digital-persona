#!/bin/sh
# Start the FastAPI service in the background. Using nohup ensures the process
# keeps running after the postStart shell exits.
# Change to the repository root so the reload watcher monitors the code
# instead of this scripts directory.
cd "$(dirname "$0")/.."

# Ensure the input directory exists so interview notes can be dropped
mkdir -p persona/input

# Reload on changes to the source tree. Watching the input folder caused the
# server to restart mid‑interview, so it has been removed from the reload paths.
nohup poetry run uvicorn digital_persona.api:create_app \
    --factory --host 0.0.0.0 --port 8000 --reload \
    --reload-dir "$(pwd)" \
    > /tmp/uvicorn.log 2>&1 &
