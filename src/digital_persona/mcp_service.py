import os

DEFAULT_PLUGINS = ["digital_persona.mcp_plugins.limitless"]

def get_plugin_names() -> list[str]:
    env = os.getenv("MCP_PLUGINS")
    if env:
        return [p.strip() for p in env.split(",") if p.strip()]
    return DEFAULT_PLUGINS.copy()

