import os
from fastapi import FastAPI, Request

from .mcp_server import create_app
from .mcp_service import DEFAULT_PLUGINS


def create_limitless_app() -> FastAPI:
    app = create_app(DEFAULT_PLUGINS)
    app.title = "limitless_mcp"

    @app.get("/.well-known/ai-plugin.json", include_in_schema=False)
    def ai_plugin(request: Request) -> dict:
        base = str(request.base_url).rstrip("/")
        return {
            "schema_version": "v1",
            "name_for_human": "Limitless MCP",
            "name_for_model": "limitless_mcp",
            "description_for_human": "Search your stored Limitless lifelogs",
            "description_for_model": "Search previously ingested lifelogs via the MCP server",
            "auth": {"type": "none"},
            "api": {
                "type": "openapi",
                "url": f"{base}{app.openapi_url}",
                "is_user_authenticated": False,
            },
        }

    return app


def _cli() -> None:
    import uvicorn

    app = create_limitless_app()
    port = int(os.getenv("MCP_PORT", "8900"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    _cli()

