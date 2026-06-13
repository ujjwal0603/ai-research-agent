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
    """Extracts text and metadata from PDF files using PyMuPDF with Gemini OCR Fallback."""

    def _is_garbage_text(self, text: str) -> bool:
        """Heuristic to determine if PyMuPDF extracted unreadable garbage."""
        if not text or not text.strip():
            return True
            
        # Count alphanumeric characters
        alnum_count = sum(c.isalnum() for c in text)
        
        # If less than 20% of the characters are alphanumeric, it's likely CID/font garbage
        if len(text) > 50 and alnum_count < 0.2 * len(text):
            return True
            
        # If total alphanumeric chars is extremely low but text length is high
        if alnum_count < 20:
            return True
            
        return False

    def _extract_text_with_gemini(self, page: fitz.Page) -> str:
        """Use Gemini 2.0 Flash as an OCR engine for image-based pages."""
        try:
            import google.generativeai as genai
            from config.settings import get_settings
            
            settings = get_settings()
            if not settings.GEMINI_API_KEY:
                logger.warning("No GEMINI_API_KEY found, skipping OCR fallback.")
                return ""
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            # Render page to image at 150 DPI for good OCR quality
            pix = page.get_pixmap(dpi=150)
            image_bytes = pix.tobytes("png")
            
            prompt = (
                "Extract all the text from this image exactly as written. "
                "Do not add any markdown formatting, headers, or extra commentary. "
                "Just return the raw text."
            )
            
            image_part = {
                "mime_type": "image/png",
                "data": image_bytes
            }
            
            response = model.generate_content([prompt, image_part])
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini OCR failed: {e}")
            return ""

    def extract_text(self, file_path: str) -> str:
        """Extract full text from all pages of a PDF, using OCR if needed."""
        pages = self.extract_text_by_page(file_path)
        full_text = "\n".join(p["text"] for p in pages)
        path = Path(file_path)
        logger.info(f"Extracted {len(full_text)} chars from {path.name}")
        return full_text

    def extract_text_by_page(self, file_path: str) -> list[dict]:
        """
        Extract text page by page with OCR fallback.

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
                
                # Check if we need OCR
                if self._is_garbage_text(text):
                    logger.info(f"Page {i+1} of {path.name} appears to be an image/garbage. Falling back to Gemini OCR...")
                    ocr_text = self._extract_text_with_gemini(page)
                    if ocr_text:
                        text = ocr_text
                
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
