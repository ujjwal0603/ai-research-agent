"""
SSE streaming utilities for the orchestrator response pipeline.

Yields Server-Sent Events in the format expected by
``sse-starlette``'s ``EventSourceResponse``.
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any, AsyncIterator, Dict, Optional

from config.constants import (
    SSE_EVENT_DONE,
    SSE_EVENT_ERROR,
    SSE_EVENT_SOURCES,
    SSE_EVENT_START,
    SSE_EVENT_TOKEN,
)

logger = logging.getLogger(__name__)


def _sse_dict(event: str, data: Any) -> Dict[str, str]:
    """Build the dict that ``EventSourceResponse`` serialises to an SSE frame."""
    return {
        "event": event,
        "data": json.dumps(data, default=str) if not isinstance(data, str) else data,
    }


async def stream_orchestrator_response(
    orchestrator: Any,
    query: str,
    context: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, str]]:
    """Async generator yielding SSE events for a streamed response.

    Event sequence:
    1. ``start``   — metadata (session_id, query echo)
    2. ``token``   — one per token / chunk of text
    3. ``sources`` — list of source chunks
    4. ``done``    — final event with full answer
    5. ``error``   — sent on failure (instead of done)

    Args:
        orchestrator: Orchestrator instance with a ``process_stream`` or
            ``process`` method.
        query: The user's question.
        context: Merged session + request context dict.
        session_id: Optional session identifier for bookkeeping.

    Yields:
        Dicts with ``event`` and ``data`` keys.
    """
    try:
        # ── Start event ─────────────────────────────
        yield _sse_dict(SSE_EVENT_START, {
            "session_id": session_id,
            "query": query,
        })

        # ── Stream tokens if orchestrator supports it ──
        if hasattr(orchestrator, "process_query_stream"):
            full_answer = ""
            sources = []
            async for chunk in orchestrator.process_query_stream(query, context):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "token":
                        token_text = chunk.get("content", "")
                        full_answer += token_text
                        yield _sse_dict(SSE_EVENT_TOKEN, {"token": token_text})
                    elif chunk.get("type") == "sources":
                        sources = chunk.get("sources", [])
                else:
                    # Plain string token
                    full_answer += str(chunk)
                    yield _sse_dict(SSE_EVENT_TOKEN, {"token": str(chunk)})

            # ── Sources event ───────────────────────
            yield _sse_dict(SSE_EVENT_SOURCES, {"sources": sources})

            # ── Done event ──────────────────────────
            yield _sse_dict(SSE_EVENT_DONE, {
                "answer": full_answer,
                "session_id": session_id,
            })

        else:
            # Fallback — non-streaming orchestrator
            result = await orchestrator.process_query(query, context)
            answer = result.get("answer", "") if isinstance(result, dict) else str(result)
            sources = result.get("sources", []) if isinstance(result, dict) else []

            # Emit as a single token
            yield _sse_dict(SSE_EVENT_TOKEN, {"token": answer})
            yield _sse_dict(SSE_EVENT_SOURCES, {"sources": sources})
            yield _sse_dict(SSE_EVENT_DONE, {
                "answer": answer,
                "session_id": session_id,
            })

    except Exception as exc:
        logger.error("SSE stream error: %s", exc, exc_info=True)
        yield _sse_dict(SSE_EVENT_ERROR, {
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })
