"""Streaming generation with Groq key rotation and a Gemini fallback.

Free-tier engineering: on a 429 the second Groq key is tried, then Gemini. Any other error
propagates — rotating keys on a 400 just burns the next key on the same bad request. Rotation
is abandoned once tokens have reached the client, since replaying would duplicate output.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from google import genai
from groq import Groq, RateLimitError

from app.config import settings

log = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
TEMPERATURE = 0.2


def groq_keys() -> list[str]:
    return [k for k in (settings.groq_api_key, settings.groq_api_key2) if k]


def _groq_stream(key: str, system: str, user: str) -> Iterator[str]:
    stream = Groq(api_key=key).chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        stream=True,
        temperature=TEMPERATURE,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def _gemini_stream(system: str, user: str) -> Iterator[str]:
    stream = genai.Client(api_key=settings.gemini_api_key).models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=user,
        config={"system_instruction": system, "temperature": TEMPERATURE},
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


def stream_chat(system: str, user: str) -> Iterator[str]:
    for index, key in enumerate(groq_keys()):
        emitted = False
        try:
            for token in _groq_stream(key, system, user):
                emitted = True
                yield token
            return
        except RateLimitError:
            if emitted:
                raise  # mid-stream: cannot restart without duplicating output
            log.warning("groq key %d rate limited, rotating", index + 1)

    log.warning("all groq keys exhausted, falling back to gemini")
    yield from _gemini_stream(system, user)


def propose_tool_calls(system: str, user: str, tools: list[dict]) -> list[dict]:
    """Ask the model which tools to call. Returns [{name, arguments}], possibly empty.

    Groq only: tool-calling schemas are not portable to the Gemini SDK, and silently degrading to
    a text answer when a caller asked for actions would be worse than failing loudly. Key rotation
    still applies — this is a single non-streaming call, so a 429 can be retried cleanly.
    """
    last: Exception | None = None
    for index, key in enumerate(groq_keys()):
        try:
            message = (
                Groq(api_key=key)
                .chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    tools=tools,
                    tool_choice="auto",
                    temperature=0,
                )
                .choices[0]
                .message
            )
            return [
                {"name": call.function.name, "arguments": json.loads(call.function.arguments)}
                for call in (message.tool_calls or [])
            ]
        except RateLimitError as exc:
            last = exc
            log.warning("groq key %d rate limited during planning, rotating", index + 1)

    raise RuntimeError("all groq keys rate limited while planning tool calls") from last
