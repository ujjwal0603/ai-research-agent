"""
PDF text extraction using PyMuPDF (fitz).

Extracts text, metadata, and page-level content from PDF documents.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text and metadata from PDF files using PyMuPDF"""

    def extract_text(self, file_path: str) -> str:
        """Extract full text from all pages of a PDF."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        text_parts = []
        with fitz.open(str(path)) as doc:
            for page in doc:
                text_parts.append(page.get_text())

        full_text = "\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from {path.name}")
        return full_text

    def extract_text_by_page(self, file_path: str) -> list[dict]:
        """
        Extract text page by page.

        Returns:
            List of dicts: [{page_number, text, char_count}, ...]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        pages = []
        with fitz.open(str(path)) as doc:
            for i, page in enumerate(doc):
                text = page.get_text()
                pages.append({
                    "page_number": i + 1,
                    "text": text,
                    "char_count": len(text),
                })

        logger.info(f"Extracted {len(pages)} pages from {path.name}")
        return pages

    def get_page_count(self, file_path: str) -> int:
        """Get the number of pages in a PDF."""
        with fitz.open(str(file_path)) as doc:
            return len(doc)

    def get_metadata(self, file_path: str) -> dict:
        """Extract PDF metadata (title, author, etc.)."""
        with fitz.open(str(file_path)) as doc:
            meta = doc.metadata or {}
            return {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "keywords": meta.get("keywords", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "page_count": len(doc),
            }
