from __future__ import annotations

from fastmcp import FastMCP

from app.services.ops_tools import build_ops_tool_registry


mcp = FastMCP("KubeMind Ops MCP")


def register_ops_tools() -> None:
    for spec in build_ops_tool_registry().values():
        mcp.tool(name=spec.name, description=spec.description)(spec.handler)


register_ops_tools()


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=11000, path="/mcp/")
