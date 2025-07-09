import os
import importlib
from fastapi import FastAPI

DEFAULT_PLUGINS = ["digital_persona.mcp_plugins.limitless"]


def create_app(plugin_names: list[str] | None = None) -> FastAPI:
    if plugin_names is None:
        env = os.getenv("MCP_PLUGINS")
        if env:
            plugin_names = [p.strip() for p in env.split(",") if p.strip()]
        else:
            plugin_names = DEFAULT_PLUGINS

    app = FastAPI(title="MCP Server")
    for name in plugin_names:
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue
        router = getattr(mod, "router", None)
        if router is not None:
            prefix = "/" + name.split(".")[-1]
            app.include_router(router, prefix=prefix)
    return app


def _cli() -> None:
    import uvicorn

    app = create_app()
    port = int(os.getenv("MCP_PORT", "8900"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    _cli()
