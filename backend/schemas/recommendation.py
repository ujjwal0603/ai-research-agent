"""
Recommendation Pydantic schemas.

Covers recommendation requests (by document or query),
individual recommendation items, and the aggregated response.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Recommendation Type ────────────────────────────


class RecommendationType(str, Enum):
    """Kind of recommendation to return."""

    RELATED_DOCUMENTS = "related_documents"
    RELATED_CONCEPTS = "related_concepts"
    SIMILAR_CHUNKS = "similar_chunks"


# ── Recommend Request ──────────────────────────────


class RecommendRequest(BaseModel):
    """Payload for the recommendation endpoint.

    At least one of ``document_id`` or ``query`` must be provided.

    Attributes:
        document_id: Base document to find recommendations for.
        query: Free-text query to find recommendations.
        recommendation_type: Kind of results to return.
        count: Number of recommendations (1-20).
    """

    document_id: Optional[str] = Field(
        default=None,
        description="Base document ID",
    )
    query: Optional[str] = Field(
        default=None,
        description="Free-text recommendation query",
    )
    recommendation_type: RecommendationType = Field(
        ...,
        description="Kind of recommendation",
    )
    count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of recommendations to return",
    )


# ── Recommendation Item ────────────────────────────


class Recommendation(BaseModel):
    """A single recommendation item.

    Attributes:
        title: Short title / label.
        description: Longer description or snippet.
        similarity_score: How similar / relevant (0–1).
        source: Source document name or concept label.
        recommendation_type: Category of this recommendation.
    """

    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Description or snippet")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity / relevance score",
    )
    source: str = Field(
        ...,
        description="Source document name or concept",
    )
    recommendation_type: RecommendationType = Field(
        ...,
        description="Recommendation category",
    )


# ── Recommend Response ─────────────────────────────


class RecommendResponse(BaseModel):
    """Aggregated recommendation response.

    Attributes:
        recommendations: List of recommendation items.
        query: The query that was used (if any).
        document_id: The document ID that was used (if any).
    """

    recommendations: List[Recommendation] = Field(
        ...,
        description="Recommendation results",
    )
    query: Optional[str] = Field(
        default=None,
        description="Query used for recommendations",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Document ID used for recommendations",
    )
