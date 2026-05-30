"""
Text chunking service with paragraph-aware splitting.

Splits documents into overlapping chunks that respect paragraph
boundaries. Falls back to sentence/word splitting for long paragraphs.
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ChunkingService:
    """Split text into semantic chunks for embedding and retrieval"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Args:
            chunk_size: Target character count per chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"ChunkingService initialized (size={chunk_size}, overlap={chunk_overlap})")

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into overlapping chunks with metadata.

        Uses paragraph boundaries where possible, falls back to
        sentence/word-level splitting for very long paragraphs.

        Args:
            text: Input text to chunk
            metadata: Additional metadata to attach to each chunk

        Returns:
            List of chunk dicts with text, chunk_index, char_count, and metadata
        """
        if not text or not text.strip():
            return []

        # Split into paragraphs (double newline or single newline)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # If adding this paragraph stays under chunk_size
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(current_chunk)

                # If paragraph itself exceeds chunk_size, split it
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_text(para)
                    # Add all but last as complete chunks
                    chunks.extend(sub_chunks[:-1])
                    # Last sub-chunk becomes the start of next chunk
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = para

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap between consecutive chunks
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        # Build result with metadata
        result = []
        base_meta = metadata or {}

        for i, chunk_text in enumerate(chunks):
            chunk_data = {
                "chunk_index": i,
                "text": chunk_text,
                "char_count": len(chunk_text),
                **base_meta,
            }
            result.append(chunk_data)

        logger.info(f"Created {len(result)} chunks from {len(text)} chars")
        return result

    def _split_long_text(self, text: str) -> List[str]:
        """Split text that exceeds chunk_size by sentences, then words"""
        # Try splitting by sentence endings
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current) + len(sentence) + 1 <= self.chunk_size:
                current = (current + " " + sentence) if current else sentence
            else:
                if current:
                    chunks.append(current)

                # If single sentence is too long, split by words
                if len(sentence) > self.chunk_size:
                    words = sentence.split()
                    current = ""
                    for word in words:
                        if len(current) + len(word) + 1 <= self.chunk_size:
                            current = (current + " " + word) if current else word
                        else:
                            if current:
                                chunks.append(current)
                            current = word
                else:
                    current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text]

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Prepend overlap from previous chunk to each subsequent chunk"""
        if self.chunk_overlap <= 0:
            return chunks

        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            # Take the tail of the previous chunk as overlap
            prev_tail = chunks[i - 1][-self.chunk_overlap:]
            # Find a word boundary in the overlap
            space_idx = prev_tail.find(" ")
            if space_idx != -1:
                prev_tail = prev_tail[space_idx + 1:]
            overlapped.append(prev_tail + " " + chunks[i])

        return overlapped
