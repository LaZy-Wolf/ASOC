"""CrewAI tool wrappers over the same MCP server the LangGraph executor drives.

Deliberately a *separate* client from backend/app/mcp_client.py. The comparison is that both
stacks talk to the same MCP server; sharing client code would hide exactly the integration work
being compared.

Tools are built from the schemas the server advertises, so neither side hardcodes a tool list.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from pydantic import BaseModel, create_model

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp-server" / "server.py"
SERVER_PYTHON = ROOT / "mcp-server" / ".venv" / "Scripts" / "python.exe"

WRITE_TOOLS = {"create_ticket", "update_ticket", "log_interaction", "schedule_maintenance_window"}

JSON_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool}

# every call the crew makes, in order, for the comparison report
CALLS: list[dict] = []


def _client() -> Client:
    return Client(
        PythonStdioTransport(
            script_path=str(SERVER),
            python_cmd=str(SERVER_PYTHON) if SERVER_PYTHON.exists() else "python",
            env={**os.environ},  # carries ASOC_DB_PATH into the spawned server
        )
    )


async def _list() -> list:
    async with _client() as client:
        return await client.list_tools()


async def _call(name: str, arguments: dict) -> Any:
    async with _client() as client:
        return (await client.call_tool(name, arguments)).data


def _args_model(name: str, schema: dict) -> type[BaseModel]:
    required = set(schema.get("required", []))
    fields = {
        key: (JSON_TYPES.get(spec.get("type"), str), ... if key in required else spec.get("default"))
        for key, spec in schema.get("properties", {}).items()
    }
    return create_model(f"{name}_args", **fields)


class MCPTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel]

    def _run(self, **kwargs) -> str:
        arguments = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        try:
            result = asyncio.run(_call(self.name, arguments))
            CALLS.append({"tool": self.name, "arguments": arguments, "ok": True})
            return str(result)
        except Exception as exc:
            CALLS.append({"tool": self.name, "arguments": arguments, "ok": False})
            return f"error: {exc}"


def load_tools() -> list[MCPTool]:
    """Discover the server's tools and wrap each one for CrewAI."""
    return [
        MCPTool(
            name=t.name,
            description=(t.description or "").strip(),
            args_schema=_args_model(t.name, t.inputSchema),
        )
        for t in asyncio.run(_list())
    ]
