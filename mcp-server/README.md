# ASOC IT-operations MCP server

Eight tools over a SQLite store. Four read, four write. The read/write split is the point: the
P4 orchestrator gates every write behind a human approval and lets reads through.

| Read | Write |
|---|---|
| `search_tickets` | `create_ticket` |
| `get_user` | `update_ticket` |
| `get_asset` | `log_interaction` |
| `find_oncall` | `schedule_maintenance_window` |

## Run

```bash
cd mcp-server && ./.venv/Scripts/python.exe server.py
```

Speaks MCP over stdio. `db.init()` creates and seeds `asoc.db` on first start.

## Test

```bash
cd mcp-server && ./.venv/Scripts/python.exe -m pytest -q
```

13 tests: every tool's happy path and a rejected bad input, plus one round trip over the real
MCP protocol (schema validation and serialisation, which direct calls skip).

## Inspect

```bash
npx @modelcontextprotocol/inspector mcp-server/.venv/Scripts/python.exe mcp-server/server.py
```

## Connect to Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json`, then restart Claude Desktop:

```json
{
  "mcpServers": {
    "asoc-itsm": {
      "command": "C:\\Users\\gugul\\Downloads\\ASOC\\mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\gugul\\Downloads\\ASOC\\mcp-server\\server.py"]
    }
  }
}
```

Then ask Claude: *"Open a P3 hardware ticket for mira.kovac@example.com — her laptop will not
power on."* The row lands in `mcp-server/asoc.db`.

## Seeded data

Seven users, five assets, four tickets, five on-call entries — consistent with the corpus in
`data/corpus/`, so a question answered from a runbook can be actioned against real rows.
Emails follow `first.last@example.com`; asset tags look like `LT-4471`.
