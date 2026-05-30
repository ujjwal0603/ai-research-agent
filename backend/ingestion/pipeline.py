"""
Full document ingestion pipeline.

Orchestrates the complete flow: PDF extraction → chunking →
metadata enrichment → vector indexing in Qdrant.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from config.constants import DocumentStatus

if TYPE_CHECKING:
    from ingestion.pdf_extractor import PDFExtractor
    from ingestion.chunking import ChunkingEngine
    from ingestion.metadata_enricher import MetadataEnricher
    from ingestion.index_builder import IndexBuilder

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates full document ingestion from PDF to vector index"""

    def __init__(
        self,
        pdf_extractor: PDFExtractor,
        chunking_engine: ChunkingEngine,
        metadata_enricher: MetadataEnricher,
        index_builder: IndexBuilder,
    ) -> None:
        self._extractor = pdf_extractor
        self._chunker = chunking_engine
        self._enricher = metadata_enricher
        self._indexer = index_builder

    async def process_document(
        self,
        file_path: str,
        document_id: str,
        filename: str,
        user_id: str,
    ) -> dict:
        """
        Run the full ingestion pipeline on a PDF document.

        Steps:
            1. Extract text by page (PyMuPDF)
            2. Chunk each page's text
            3. Enrich chunks with metadata
            4. Embed and index in Qdrant

        Args:
            file_path: Path to the uploaded PDF
            document_id: UUID for the document
            filename: Original filename
            user_id: UUID of the uploading user

        Returns:
            Dict with page_count, chunk_count, status
        """
        start = time.perf_counter()
        logger.info(f"Starting ingestion for '{filename}' (doc_id={document_id})")

        try:
            # 1. Extract text by page
            logger.info(f"[1/4] Extracting text from {filename}...")
            pages = self._extractor.extract_text_by_page(file_path)
            page_count = len(pages)

            if page_count == 0:
                logger.warning(f"No pages extracted from {filename}")
                return {
                    "page_count": 0,
                    "chunk_count": 0,
                    "status": DocumentStatus.FAILED,
                    "error": "No text content found in PDF",
                }

            # 2. Chunk pages
            logger.info(f"[2/4] Chunking {page_count} pages...")
            chunks = self._chunker.chunk_pages(pages)

            if not chunks:
                logger.warning(f"No chunks generated from {filename}")
                return {
                    "page_count": page_count,
                    "chunk_count": 0,
                    "status": DocumentStatus.FAILED,
                    "error": "No text chunks could be generated",
                }

            # 3. Enrich with metadata
            logger.info(f"[3/4] Enriching {len(chunks)} chunks with metadata...")
            doc_meta = {
                "document_id": document_id,
                "filename": filename,
                "user_id": user_id,
            }
            enriched_chunks = await self._enricher.enrich(chunks, doc_meta)

            # 4. Build vector index
            logger.info(f"[4/4] Building vector index ({len(enriched_chunks)} chunks)...")
            chunk_count = await self._indexer.build_index(
                document_id, enriched_chunks
            )

            elapsed = time.perf_counter() - start
            logger.info(
                f"Ingestion complete for '{filename}': "
                f"{page_count} pages, {chunk_count} chunks, "
                f"{elapsed:.1f}s elapsed"
            )

            return {
                "page_count": page_count,
                "chunk_count": chunk_count,
                "status": DocumentStatus.PROCESSED,
            }

        except FileNotFoundError as exc:
            logger.error(f"File not found: {file_path}")
            return {
                "page_count": 0,
                "chunk_count": 0,
                "status": DocumentStatus.FAILED,
                "error": str(exc),
            }
        except Exception as exc:
            logger.exception(f"Ingestion failed for '{filename}': {exc}")
            return {
                "page_count": 0,
                "chunk_count": 0,
                "status": DocumentStatus.FAILED,
                "error": str(exc),
            }
