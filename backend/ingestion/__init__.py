"""
Ingestion package — PDF extraction, chunking, metadata enrichment, and indexing.

Provides the full document processing pipeline from raw PDF to indexed vectors.
"""

from __future__ import annotations

from ingestion.pipeline import IngestionPipeline

__all__ = ["IngestionPipeline"]
