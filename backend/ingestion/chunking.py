"""
Paragraph-aware text chunking engine.

Splits document text into overlapping chunks while respecting
paragraph boundaries for better semantic coherence.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class ChunkingEngine:
    """Splits text into semantically coherent chunks with overlap"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        """
        Split text into overlapping chunks, respecting paragraph boundaries.

        Args:
            text: Full document text
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dicts with chunk_index, text, char_count, and metadata
        """
        if not text or not text.strip():
            return []

        meta = metadata or {}

        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for paragraph in paragraphs:
            # If adding this paragraph exceeds chunk_size, finalize current chunk
            if current_chunk and len(current_chunk) + len(paragraph) + 1 > self.chunk_size:
                chunks.append(self._make_chunk(
                    current_chunk, chunk_index, meta
                ))
                chunk_index += 1

                # Keep overlap from end of previous chunk
                if self.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

            # Handle paragraphs larger than chunk_size
            while len(current_chunk) > self.chunk_size:
                # Find a good split point (sentence boundary)
                split_at = self._find_split_point(current_chunk, self.chunk_size)
                chunk_text = current_chunk[:split_at].strip()

                if chunk_text:
                    chunks.append(self._make_chunk(
                        chunk_text, chunk_index, meta
                    ))
                    chunk_index += 1

                # Keep overlap
                remaining = current_chunk[split_at:].strip()
                if self.chunk_overlap > 0 and len(chunk_text) > self.chunk_overlap:
                    overlap = chunk_text[-self.chunk_overlap:]
                    current_chunk = overlap + " " + remaining
                else:
                    current_chunk = remaining

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(self._make_chunk(
                current_chunk.strip(), chunk_index, meta
            ))

        logger.info(
            f"Chunked text into {len(chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return chunks

    def chunk_pages(self, pages: list[dict], metadata: dict | None = None) -> list[dict]:
        """
        Chunk a list of page dicts, preserving page number metadata.

        Args:
            pages: List of {page_number, text, char_count} dicts
            metadata: Additional metadata

        Returns:
            List of chunk dicts with page_number included
        """
        all_chunks = []
        chunk_index = 0

        for page in pages:
            page_meta = {**(metadata or {}), "page_number": page["page_number"]}
            page_chunks = self.chunk_text(page["text"], page_meta)

            for chunk in page_chunks:
                chunk["chunk_index"] = chunk_index
                chunk_index += 1

            all_chunks.extend(page_chunks)

        logger.info(f"Chunked {len(pages)} pages into {len(all_chunks)} chunks")
        return all_chunks

    def _make_chunk(self, text: str, index: int, metadata: dict) -> dict:
        """Create a chunk dict with metadata"""
        return {
            "chunk_index": index,
            "text": text,
            "char_count": len(text),
            **metadata,
        }

    def _find_split_point(self, text: str, max_pos: int) -> int:
        """Find the best split point near max_pos (prefer sentence boundaries)"""
        # Try sentence-ending punctuation
        for sep in [". ", ".\n", "? ", "! ", "; "]:
            pos = text.rfind(sep, 0, max_pos)
            if pos > max_pos * 0.5:
                return pos + len(sep)

        # Fall back to word boundary
        pos = text.rfind(" ", 0, max_pos)
        if pos > max_pos * 0.3:
            return pos + 1

        # Last resort: hard split
        return max_pos
