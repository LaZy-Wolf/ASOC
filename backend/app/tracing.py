"""Langfuse tracing, optional by design.

Observability must not be a hard dependency of answering a question. If the keys are absent or
the container is down, nodes run untraced rather than failing — an agent that stops working
because its telemetry sink is unreachable is a worse outcome than one you cannot see into.

Uses Langfuse's native `@observe` rather than its LangChain callback handler: the handler pulls in
the whole `langchain` package, which this project deliberately does not use. The decorator gives
one span per graph node, nested under the run, with no framework in between.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from app.config import settings

log = logging.getLogger(__name__)

_enabled: bool | None = None


def enabled() -> bool:
    """True when Langfuse is reachable and the credentials are accepted. Checked once."""
    global _enabled
    if _enabled is not None:
        return _enabled

    _enabled = False
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        log.info("langfuse keys not set, tracing disabled")
        return _enabled

    # the SDK reads its own env vars; pydantic-settings loaded .env into an object, not os.environ
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    try:
        from langfuse import get_client

        if get_client().auth_check():
            _enabled = True
            log.info("langfuse tracing enabled at %s", settings.langfuse_host)
        else:
            log.warning(
                "langfuse rejected the credentials at %s — create a project in its UI and put the "
                "generated keys in .env. Continuing untraced.",
                settings.langfuse_host,
            )
    except Exception as exc:
        log.warning("langfuse unavailable, tracing disabled: %s", exc)

    return _enabled


def traced(name: str) -> Callable:
    """Decorate a graph node so it becomes a span. Identity function when tracing is off."""

    def wrap(fn: Callable) -> Callable:
        if not enabled():
            return fn
        from langfuse import observe

        return observe(name=name)(fn)

    return wrap
