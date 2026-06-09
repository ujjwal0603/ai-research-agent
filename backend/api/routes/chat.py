"""
Chat endpoint — supports both regular JSON and SSE streaming responses.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_orchestrator, get_session_manager
from api.middleware.auth import get_current_user
from api.routes.sse import stream_orchestrator_response
from config.constants import IntentType
from memory.conversation_history import ConversationHistory
from memory.shared_memory import SharedMemory
from schemas.chat import ChatRequest, ChatResponse, SourceChunk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Process a chat query using the multi-agent orchestrator.

    If ``body.stream`` is True the response is an SSE
    ``EventSourceResponse``; otherwise a regular JSON ``ChatResponse``.
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    user_id = current_user["user_id"]

    # ── Build context ───────────────────────────────
    context: Dict[str, Any] = {
        "user_id": user_id,
        "intent": IntentType.QUESTION,
        "search_strategy": body.search_strategy,
        "top_k": body.top_k,
        "document_ids": body.document_ids,
        "provider": body.provider,
    }

    # Attach session context if session_id given
    session_id = body.session_id
    session_mgr = _get_session_manager_safe()
    if session_id and session_mgr:
        sess_ctx = await session_mgr.get_context(session_id)
        context.update(sess_ctx)

    # Attach recent conversation history
    history_mgr = _get_conversation_history_safe()
    if session_id and history_mgr:
        history = await history_mgr.get_history(session_id, limit=6)
        context["conversation_history"] = history

    # ── Get orchestrator ────────────────────────────
    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialised yet — try again in a moment",
        )

    # ── Save user message ───────────────────────────
    if session_id and history_mgr:
        await history_mgr.add_message(session_id, "user", query)

    # ── Streaming path ──────────────────────────────
    if body.stream:
        return EventSourceResponse(
            orchestrator.process_query_stream(query, context)
        )

    # ── Non-streaming path ──────────────────────────
    try:
        result = await orchestrator.process_query(query, context)

        answer = result.get("answer", "") if isinstance(result, dict) else str(result)
        raw_sources = result.get("sources", []) if isinstance(result, dict) else []
        trace = result.get("trace") if isinstance(result, dict) else None

        sources = []
        for s in raw_sources:
            payload = s.get("payload", {})
            norm_s = {**payload, **s}
            sources.append(
                SourceChunk(
                    text=norm_s.get("text", ""),
                    document_name=norm_s.get("document_name", "Unknown"),
                    page_number=norm_s.get("page_number"),
                    chunk_index=norm_s.get("chunk_index", 0),
                    score=round(norm_s.get("score", 0.0), 4),
                    document_id=norm_s.get("document_id"),
                )
            )

        # Save assistant message
        if session_id and history_mgr:
            source_dicts = [s.model_dump() for s in sources]
            await history_mgr.add_message(
                session_id, "assistant", answer, sources=source_dicts
            )

        return ChatResponse(
            answer=answer,
            sources=sources,
            query=query,
            session_id=session_id,
            trace=trace,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Chat failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}")


# ── Safe lazy helpers (avoid import errors if memory not ready) ──


def _get_session_manager_safe():
    try:
        from api.dependencies import get_session_manager

        return get_session_manager()
    except Exception:
        return None


def _get_conversation_history_safe():
    try:
        from api.dependencies import get_conversation_history

        return get_conversation_history()
    except Exception:
        return None
