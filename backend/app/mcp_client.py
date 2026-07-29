"""Client for the ASOC MCP server.

Talks the real MCP protocol over stdio to `mcp-server/server.py`, the same way Claude Desktop
does. Tool schemas are discovered at runtime rather than duplicated here — the server's docstrings
and type hints are the single source of truth, so adding a tool there needs no change in this file.

Which tools are writes is decided here, not there: the server is a plain tool provider, and the
policy about what needs a human is the orchestrator's business.
"""

from __future__ import annotations

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

from app.config import ROOT

SERVER = ROOT / "mcp-server" / "server.py"
SERVER_PYTHON = ROOT / "mcp-server" / ".venv" / "Scripts" / "python.exe"

# Everything that changes state. The approval gate keys off this set.
WRITE_TOOLS = {
    "create_ticket",
    "update_ticket",
    "log_interaction",
    "schedule_maintenance_window",
}


def _client() -> Client:
    return Client(
        PythonStdioTransport(
            script_path=str(SERVER),
            python_cmd=str(SERVER_PYTHON) if SERVER_PYTHON.exists() else "python",
        )
    )


def is_write(tool_name: str) -> bool:
    return tool_name in WRITE_TOOLS


async def tool_schemas() -> list[dict]:
    """MCP tool definitions rendered as OpenAI-style function schemas for Groq tool calling."""
    async with _client() as client:
        tools = await client.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": (t.description or "").strip(),
                "parameters": t.inputSchema,
            },
        }
        for t in tools
    ]


async def call_tool(name: str, arguments: dict) -> dict:
    """Invoke one tool. Errors are returned, not raised — a failed tool call is information the
    graph should carry into its answer, not a crash."""
    try:
        async with _client() as client:
            result = await client.call_tool(name, arguments)
        return {"ok": True, "tool": name, "arguments": arguments, "result": result.data}
    except Exception as exc:
        return {"ok": False, "tool": name, "arguments": arguments, "error": str(exc)}
