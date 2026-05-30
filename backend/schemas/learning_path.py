"""
Learning-path Pydantic schemas.

Covers adaptive learning path generation, concept-graph nodes
with prerequisites, path responses, and progress tracking.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from config.constants import ConceptStatus, LearningDepth
from schemas.chat import SourceChunk

logger = logging.getLogger(__name__)


# ── Learning Path Request ──────────────────────────


class LearningPathRequest(BaseModel):
    """Payload for generating an adaptive learning path.

    Attributes:
        document_ids: Source documents to build the path from.
        current_knowledge: Concepts the learner already understands.
        learning_goal: What the learner wants to achieve.
        preferred_depth: Desired level of detail.
    """

    document_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Source document IDs",
    )
    current_knowledge: Optional[List[str]] = Field(
        default=None,
        description="Concepts the learner already knows",
    )
    learning_goal: Optional[str] = Field(
        default=None,
        description="Learning objective",
    )
    preferred_depth: LearningDepth = Field(
        default=LearningDepth.INTERMEDIATE,
        description="Desired detail level",
    )


# ── Concept Node ───────────────────────────────────


class ConceptNode(BaseModel):
    """A single node in the concept dependency graph.

    Attributes:
        concept_id: Unique concept identifier.
        name: Short concept name.
        description: Detailed description.
        prerequisites: IDs of prerequisite concepts.
        source_chunks: Chunks relevant to this concept.
        estimated_time_minutes: Estimated study time.
        status: Current learner status for this concept.
    """

    concept_id: str = Field(..., description="Unique concept ID")
    name: str = Field(..., description="Concept name")
    description: str = Field(..., description="Concept description")
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Prerequisite concept IDs",
    )
    source_chunks: List[SourceChunk] = Field(
        default_factory=list,
        description="Relevant source chunks",
    )
    estimated_time_minutes: int = Field(
        ...,
        ge=0,
        description="Estimated study time in minutes",
    )
    status: ConceptStatus = Field(
        default=ConceptStatus.LOCKED,
        description="Learner progress status",
    )


# ── Learning Path Response ─────────────────────────


class LearningPathResponse(BaseModel):
    """Full learning path returned after generation.

    Attributes:
        path_id: Unique path ID.
        title: Path title / heading.
        concepts: Ordered concept graph nodes.
        total_estimated_hours: Total estimated study time in hours.
        progress_percent: Learner's current completion percentage.
    """

    path_id: str = Field(..., description="Unique learning path ID")
    title: str = Field(..., description="Learning path title")
    concepts: List[ConceptNode] = Field(
        ...,
        description="Ordered concept nodes",
    )
    total_estimated_hours: float = Field(
        ...,
        ge=0.0,
        description="Total estimated study hours",
    )
    progress_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Completion percentage (0–100)",
    )


# ── Progress Update ────────────────────────────────


class ProgressUpdate(BaseModel):
    """Marks a concept as completed or available.

    Attributes:
        concept_id: The concept to update.
        status: New status for the concept.
    """

    concept_id: str = Field(..., description="Concept ID to update")
    status: ConceptStatus = Field(
        ...,
        description="New status (completed / available)",
    )
