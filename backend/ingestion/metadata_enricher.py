"""
Metadata enricher for document chunks.

Adds document-level metadata to each chunk. In Phase 4, this will
integrate with the ClassificationModel for domain classification
and entity extraction.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models_layer.classification_model import ClassificationModel

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Enriches chunks with document and domain metadata"""

    def __init__(self, classification_model: ClassificationModel | None = None) -> None:
        self._classifier = classification_model

    async def enrich(
        self, chunks: list[dict], document_metadata: dict
    ) -> list[dict]:
        """
        Enrich each chunk with document-level metadata.

        Args:
            chunks: List of chunk dicts from ChunkingEngine
            document_metadata: Document-level info (document_id, filename, etc.)

        Returns:
            Enriched chunk list with added metadata fields
        """
        doc_id = document_metadata.get("document_id", "")
        filename = document_metadata.get("filename", "")
        user_id = document_metadata.get("user_id", "")

        enriched = []
        for chunk in chunks:
            enriched_chunk = {
                **chunk,
                "document_id": doc_id,
                "filename": filename,
                "user_id": user_id,
                "document_name": filename,
            }
            enriched.append(enriched_chunk)

        logger.info(
            f"Enriched {len(enriched)} chunks with metadata "
            f"for document {filename}"
        )
        return enriched
