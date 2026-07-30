"""The plan-then-execute slice, rebuilt in CrewAI.

Scope is deliberately narrow: only the part of the LangGraph graph that turns a request into tool
calls and runs them. Retrieval, the confidence gate and the streaming UI are not reimplemented —
this is a framework comparison, not a rewrite.

Two agents mirror what LangGraph does in two nodes (plan, execute). CrewAI reaches Groq through
litellm, so the two-key rotation in backend/app/llm.py does not apply here; see NOTES.md.
"""

from __future__ import annotations

import os
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task

from mcp_tools import CALLS, load_tools

# Groq matches the LangGraph side, which is the fair comparison. ASOC_CREW_MODEL=gemini switches
# to a CrewAI *native* provider — useful both when Groq's daily cap is spent and as a check that
# the cache_breakpoint problem below really is confined to the litellm path.
MODELS = {
    "groq": ("groq/llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "gemini": ("gemini/gemini-2.0-flash", "GEMINI_API_KEY"),
}
PROVIDER = os.environ.get("ASOC_CREW_MODEL", "groq")


def _env_value(name: str) -> str:
    """Read a key straight out of the repo .env — no pydantic-settings in this venv."""
    for line in (Path(__file__).resolve().parents[1] / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"{name} not found in .env")


def _patch_cache_breakpoint() -> None:
    """Work around a CrewAI/litellm/Groq incompatibility.

    CrewAI's agent executor marks messages with `cache_breakpoint: True` and expects the provider
    adapter to translate or strip it (its own docstring: adapters "strip it for providers that
    cache implicitly ... or do not cache at all"). The litellm fallback path has no such adapter,
    so the raw marker is sent as a message property and Groq rejects it:

        GroqException - 'messages.0' : for 'role:system' the following must be satisfied
        [('messages.0' : property 'cache_breakpoint' is unsupported)]

    Groq is not one of CrewAI's native providers, so litellm is the only route to it — which makes
    CrewAI + Groq unusable without this. Stripping the key on the way out costs nothing, since
    Groq does not support explicit cache breakpoints anyway.
    """
    import litellm

    for name in ("completion", "acompletion"):
        original = getattr(litellm, name, None)
        if original is None:
            continue

        def strip(*args, _original=original, **kwargs):
            for message in kwargs.get("messages") or []:
                if isinstance(message, dict):
                    message.pop("cache_breakpoint", None)
            return _original(*args, **kwargs)

        setattr(litellm, name, strip)


def build_crew(human_input: bool = False) -> Crew:
    """The crew. `human_input=True` is CrewAI's approval story — a blocking stdin prompt."""
    model, key_name = MODELS[PROVIDER]
    os.environ[key_name] = _env_value(key_name)
    if PROVIDER == "gemini":
        os.environ.setdefault("GOOGLE_API_KEY", os.environ[key_name])
    _patch_cache_breakpoint()
    llm = LLM(model=model, temperature=0)
    tools = load_tools()

    dispatcher = Agent(
        role="IT operations dispatcher",
        goal=(
            "Turn a helpdesk request into the smallest correct set of tool calls, and run them. "
            "If the request only asks a question, call nothing."
        ),
        backstory=(
            "You run an internal IT desk. You set priority by impact, not by the words the "
            "requester used: P1 total loss or data exposure, P2 someone fully blocked, P3 partial "
            "or a workaround exists, P4 routine requests. You never invent an email address or an "
            "asset tag that was not supplied."
        ),
        tools=tools,
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description="Handle this helpdesk request:\n\n{request}",
        expected_output=(
            "One short paragraph stating what you did, naming each tool you called. If you called "
            "nothing, say so and answer the question directly."
        ),
        agent=dispatcher,
        human_input=human_input,
    )

    return Crew(agents=[dispatcher], tasks=[task], process=Process.sequential, verbose=False)


def run(request: str) -> tuple[str, list[dict]]:
    """Run one request. Returns (final answer, tool calls made)."""
    CALLS.clear()
    result = build_crew().kickoff(inputs={"request": request})
    return str(result), list(CALLS)


if __name__ == "__main__":
    import sys

    answer, calls = run(sys.argv[1] if len(sys.argv) > 1 else "Who is on call for platform?")
    print("\n--- tool calls ---")
    for call in calls:
        print(f"  {call['tool']} ok={call['ok']} {call['arguments']}")
    print("\n--- answer ---")
    print(answer)
