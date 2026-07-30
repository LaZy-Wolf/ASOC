"""Run the same fixtures through the CrewAI implementation. Use the COMPARE venv.

    cd compare && ./.venv/Scripts/python.exe run_crewai.py

Writes compare/results_crewai.json.

`gated` is always False here, and that is the finding rather than an oversight: CrewAI's approval
mechanism is `human_input=True`, which blocks on stdin inside the kickoff. It cannot be driven
non-interactively and cannot resume after the process exits, so there is nothing to record.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRATCH = ROOT / "compare" / "scratch_crewai.db"
shutil.copy(ROOT / "mcp-server" / "asoc.db", SCRATCH)
os.environ["ASOC_DB_PATH"] = str(SCRATCH)

from crew_impl import run  # noqa: E402
from mcp_tools import WRITE_TOOLS  # noqa: E402

FIXTURES = ROOT / "compare" / "fixtures.jsonl"
OUT = ROOT / "compare" / "results_crewai.json"


def main() -> int:
    fixtures = [json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []

    for fixture in fixtures:
        started = time.perf_counter()
        try:
            _, calls = run(fixture["request"])
            error = None
        except Exception as exc:
            calls, error = [], str(exc)[:200]

        tools = [c["tool"] for c in calls]
        result = {
            "id": fixture["id"],
            "tools": tools,
            "writes": sum(1 for t in tools if t in WRITE_TOOLS),
            "gated": False,
            "correct_tools": set(tools) == set(fixture["expect_tools"]),
            "seconds": round(time.perf_counter() - started, 2),
            "error": error,
        }
        print(f"  {result['id']:22s} tools={tools} error={error}")
        results.append(result)

    OUT.write_text(json.dumps({"stack": "crewai", "results": results}, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
