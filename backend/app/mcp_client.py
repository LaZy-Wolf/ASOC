"""Client for the ASOC MCP server.

Talks the real MCP protocol over stdio to `mcp-server/server.py`, the same way Claude Desktop
does. Tool schemas are discovered at runtime rather than duplicated here — the server's docstrings
and type hints are the single source of truth, so adding a tool there needs no change in this file.

Which tools are writes is decided here, not there: the server is a plain tool provider, and the
policy about what needs a human is the orchestrator's business.
"""

from __future__ import annotations

import os

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
            # the child does not inherit our environment by default, so ASOC_DB_PATH would be
            # dropped and the server would silently use the real database — which is how the
            # framework comparison first wrote its fixtures into production seed data
            env={**os.environ},
        )
    )


def is_write(tool_name: str) -> bool:
    return tool_name in WRITE_TOOLS


def _relax_integers(schema: dict) -> dict:
    """Let integer parameters also accept a string in the schema advertised to the model.

    Groq validates tool calls against the schema we send and rejects mismatches. For
    "Move ticket 1 to in-progress" the model reliably emits `{"ticket_id": "1"}` — a quoted
    integer — and the call is refused before it ever reaches us. That reproduced across both API
    keys and at two temperatures, so it is systematic, not a sampling fluke.

    Widening here rather than on the server keeps the MCP contract strict for well-behaved clients;
    `_coerce` converts the value back before dispatch.
    """
    relaxed = {k: v for k, v in schema.items()}
    properties = {}
    for name, spec in schema.get("properties", {}).items():
        if spec.get("type") == "integer":
            spec = {**spec, "type": ["integer", "string"]}
        properties[name] = spec
    relaxed["properties"] = properties
    return relaxed


def _coerce(arguments: dict, schema: dict) -> dict:
    """Cast quoted numbers back to integers, per the server's real schema."""
    properties = schema.get("properties", {})
    out = {}
    for name, value in arguments.items():
        if properties.get(name, {}).get("type") == "integer" and isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError:
                pass  # let the server reject it with a useful message
        out[name] = value
    return out


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
                "parameters": _relax_integers(t.inputSchema),
            },
        }
        for t in tools
    ]


async def call_tool(name: str, arguments: dict) -> dict:
    """Invoke one tool. Errors are returned, not raised — a failed tool call is information the
    graph should carry into its answer, not a crash."""
    try:
        # one session for both the schema lookup and the call: a second Client on the same
        # keep-alive transport reuses the closed session and fails with "client has been closed"
        async with _client() as client:
            schemas = {t.name: t.inputSchema for t in await client.list_tools()}
            arguments = _coerce(arguments, schemas.get(name, {}))
            result = await client.call_tool(name, arguments)
        return {"ok": True, "tool": name, "arguments": arguments, "result": result.data}
    except Exception as exc:
        return {"ok": False, "tool": name, "arguments": arguments, "error": str(exc)}
