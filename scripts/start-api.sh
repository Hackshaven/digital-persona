#!/bin/sh
# Start the FastAPI service in the background. Using nohup ensures the process
# keeps running after the postStart shell exits.
# Change to the repository root so the reload watcher monitors the code
# instead of this scripts directory.
cd "$(dirname "$0")/.."

# Ensure the input directory exists so uvicorn can watch it
mkdir -p persona/input

# Reload on changes to the source tree and to incoming interview notes so
# developers can drop new files into ``persona/input`` and see them picked up
# immediately.
nohup poetry run uvicorn digital_persona.api:create_app \
    --factory --host 0.0.0.0 --port 8000 --reload \
    --reload-dir "$(pwd)" --reload-dir "$(pwd)/persona/input" \
    > /tmp/uvicorn.log 2>&1 &
