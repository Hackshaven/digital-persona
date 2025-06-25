#!/bin/sh
# Start the FastAPI service in the background. Using nohup ensures the process
# keeps running after the postStart shell exits.
nohup poetry run uvicorn digital_persona.api:create_app \
    --factory --host 0.0.0.0 --port 8000 --reload \
    > /tmp/uvicorn.log 2>&1 &
