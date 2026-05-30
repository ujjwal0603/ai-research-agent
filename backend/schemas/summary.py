"""
Document summarisation Pydantic schemas.

Covers the summarise request (type, focus topics, length),
section-level structure, and the full summary response.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from config.constants import SummaryType
from schemas.chat import Citation

logger = logging.getLogger(__name__)


# ── Summarize Request ──────────────────────────────


class SummarizeRequest(BaseModel):
    """Payload for the document summarisation endpoint.

    Attributes:
        document_ids: Documents to summarise.
        summary_type: Style of summary to produce.
        max_length: Optional maximum word count.
        focus_topics: Optional topics to emphasise.
    """

    document_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Document IDs to summarise",
    )
    summary_type: SummaryType = Field(
        ...,
        description="Summary style (executive / section / bullet / abstract)",
    )
    max_length: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum word count (optional)",
    )
    focus_topics: Optional[List[str]] = Field(
        default=None,
        description="Topics to emphasise in the summary",
    )


# ── Summary Section ────────────────────────────────


class SummarySection(BaseModel):
    """A titled section within a structured summary.

    Attributes:
        title: Section heading.
        content: Section body text.
        source_references: Document/page references supporting this section.
    """

    title: str = Field(..., description="Section heading")
    content: str = Field(..., description="Section body text")
    source_references: List[str] = Field(
        default_factory=list,
        description="Source references (e.g. doc:page pairs)",
    )


# ── Summary Response ───────────────────────────────


class SummaryResponse(BaseModel):
    """Full summary returned from the summarisation endpoint.

    Attributes:
        summary_id: Unique ID for this summary.
        summary: Plain-text (or markdown) summary.
        sections: Structured sections (for ``section`` summary type).
        citations: Citations supporting the summary claims.
        word_count: Actual word count of the summary.
        document_coverage: Fraction of source content covered (0–1).
    """

    summary_id: str = Field(..., description="Unique summary ID")
    summary: str = Field(..., description="Full summary text")
    sections: Optional[List[SummarySection]] = Field(
        default=None,
        description="Structured sections (section-type summaries)",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Supporting citations",
    )
    word_count: int = Field(..., ge=0, description="Summary word count")
    document_coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Source content coverage fraction (0–1)",
    )
