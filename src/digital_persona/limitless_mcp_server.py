import os
from fastapi import FastAPI

from .mcp_server import create_app
from .mcp_service import DEFAULT_PLUGINS


def create_limitless_app() -> FastAPI:
    app = create_app(DEFAULT_PLUGINS)
    app.title = "limitless_mcp"

    return app


def _cli() -> None:
    import uvicorn

    app = create_limitless_app()
    port = int(os.getenv("MCP_PORT", "8900"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    _cli()

