"""Prompt-injection containment.

Retrieved documents feed a tool-calling agent, which is the classic injection surface: anyone who
can get text into the corpus can try to address the model directly. A wiki anyone can edit is a
realistic attack path.

Three layers, because no single one is sufficient:

1. Retrieved text is fenced and labelled as data. Necessary, not sufficient — a determined
   injection can talk its way past a delimiter.
2. Tool calls are checked against the server's own tool list. A call to something never advertised
   is dropped outright.
3. Every write still stops at the human approval gate. That is the layer that actually holds, and
   it is why the gate is not merely a UX nicety.
"""

from __future__ import annotations

import re

FENCE = "-----"

# Phrases whose only purpose is to redirect the model. Matching them is a signal, not a defence:
# the fence and the approval gate do the real work.
SUSPICIOUS = re.compile(
    r"\b((?:ignore|disregard) (?:all |any |the )?(?:previous|prior|above)"
    r"(?: instructions?| prompts?| rules?)?|"
    r"you are now|new instructions?|system prompt|reveal your|"
    r"do not (?:ask|require|wait for) (?:for )?(?:approval|confirmation|permission))\b",
    re.I,
)


def fence(text: str) -> str:
    """Wrap retrieved content so the model can tell where data starts and stops.

    Any fence sequence occurring inside the text is defanged, otherwise a document could close
    the fence early and continue as if it were prompt.
    """
    return f"{FENCE}\n{text.replace(FENCE, '- - -')}\n{FENCE}"


def flag_injection(text: str) -> list[str]:
    """Injection-shaped phrases found in retrieved text. For logging and tests."""
    return sorted({m.group(0).lower() for m in SUSPICIOUS.finditer(text)})


def allowed_calls(calls: list[dict], available: set[str]) -> tuple[list[dict], list[dict]]:
    """Split proposed tool calls into (allowed, blocked) against the server's advertised tools."""
    allowed, blocked = [], []
    for call in calls:
        (allowed if call.get("name") in available else blocked).append(call)
    return allowed, blocked
