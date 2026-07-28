"""Streaming generation with Groq key rotation and a Gemini fallback.

Free-tier engineering: on a 429 the second Groq key is tried, then Gemini. Any other error
propagates — rotating keys on a 400 just burns the next key on the same bad request. Rotation
is abandoned once tokens have reached the client, since replaying would duplicate output.
"""

from __future__ import annotations

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
