"""
Summarization endpoint.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session, get_orchestrator
from api.middleware.auth import get_current_user
from config.constants import IntentType
from schemas.summary import SummarizeRequest, SummaryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["summarize"])


@router.post("/summarize", response_model=SummaryResponse)
async def summarize(
    body: SummarizeRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Generate a summary for one or more documents.

    Uses the orchestrator with ``IntentType.SUMMARIZE`` so the
    summarisation agent is invoked.
    """
    user_id = current_user["user_id"]

    # Validate that document_ids belong to the user
    try:
        from database.models import Document

        result = await session.execute(
            select(Document).where(
                Document.id.in_([uuid.UUID(d) for d in body.document_ids]),
                Document.user_id == uuid.UUID(user_id),
            )
        )
        found_docs = result.scalars().all()
        found_ids = {doc.id for doc in found_docs}
        missing = set(body.document_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documents not found: {', '.join(missing)}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Document validation skipped: %s", exc)

    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised")

    context: Dict[str, Any] = {
        "user_id": user_id,
        "intent": IntentType.SUMMARIZE,
        "document_ids": body.document_ids,
        "summary_type": body.summary_type,
        "max_length": body.max_length,
        "provider": body.provider,
    }

    try:
        result = await orchestrator.process(
            query=f"Summarize documents: {', '.join(body.document_ids)}",
            context=context,
        )

        summary_text = result.get("answer", "") if isinstance(result, dict) else str(result)
        sections = result.get("sections", []) if isinstance(result, dict) else []

        return SummaryResponse(
            summary=summary_text,
            sections=sections,
            document_ids=body.document_ids,
            summary_type=body.summary_type,
            word_count=len(summary_text.split()),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Summarization failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summarization failed: {exc}")
