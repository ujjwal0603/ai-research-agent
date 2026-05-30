"""
PDF text extraction service using PyMuPDF (fitz).

Handles:
- Full text extraction
- Page-by-page extraction with metadata
- PDF metadata extraction
- Page count retrieval
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PDFService:
    """Extract text and metadata from PDF files using PyMuPDF"""

    def extract_text(self, file_path: str) -> str:
        """
        Extract all text from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Combined text from all pages

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        doc = fitz.open(file_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                text_parts.append(text)

        page_count = len(doc)
        doc.close()

        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from {page_count} pages: {path.name}")

        return full_text

    def extract_text_by_page(self, file_path: str) -> List[Dict]:
        """
        Extract text page-by-page with metadata.

        Returns:
            List of dicts with page_number, text, and char_count
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        doc = fitz.open(file_path)
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            pages.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
            })

        doc.close()
        return pages

    def get_page_count(self, file_path: str) -> int:
        """Get number of pages in a PDF"""
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count

    def get_metadata(self, file_path: str) -> Dict:
        """Extract PDF metadata (title, author, etc.)"""
        doc = fitz.open(file_path)
        metadata = doc.metadata or {}
        page_count = len(doc)
        doc.close()

        return {
            "page_count": page_count,
            "title": metadata.get("title", "").strip() or None,
            "author": metadata.get("author", "").strip() or None,
            "subject": metadata.get("subject", "").strip() or None,
        }
