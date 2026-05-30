import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.utils import setup_logger

logger = setup_logger(__name__)

@dataclass
class PageContent:
    """Single page extraction result"""
    page_number: int
    text: str
    blocks: List[Dict]  # Raw text blocks from PyMuPDF
    char_count: int
    line_count: int

@dataclass
class ExtractionMetadata:
    """Metadata about extraction process"""
    total_pages: int
    total_chars: int
    total_lines: int
    extraction_time: float
    success_pages: int
    failed_pages: int
    errors: List[str]

class PDFExtractor:
    """
    Extract text from PDF using PyMuPDF (fitz)

    Features:
    - Page-by-page extraction
    - Metadata extraction
    - Error recovery
    - Text block analysis
    - Layout-aware text extraction
    """

    def __init__(self, preserve_layout: bool = True):
        """
        Initialize extractor

        Args:
            preserve_layout: Preserve text layout and spacing
        """
        self.preserve_layout = preserve_layout
        logger.info(f"PDFExtractor initialized (preserve_layout={preserve_layout})")

    def extract_text(self, file_path: str) -> Tuple[str, ExtractionMetadata]:
        """
        Extract all text from PDF

        Args:
            file_path: Path to PDF file

        Returns:
            (full_text: str, metadata: ExtractionMetadata)
        """
        import time
        start_time = time.time()

        if not Path(file_path).exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        pages_content = []
        errors = []
        failed_pages = 0

        try:
            pdf_document = fitz.open(file_path)
            logger.info(f"Opened PDF: {file_path} with {len(pdf_document)} pages")

            for page_num in range(len(pdf_document)):
                try:
                    page_content = self._extract_page_text(pdf_document, page_num)
                    pages_content.append(page_content)

                except Exception as e:
                    error_msg = f"Failed to extract page {page_num + 1}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    failed_pages += 1

            pdf_document.close()

        except Exception as e:
            error_msg = f"Failed to open PDF {file_path}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        # Combine all pages
        full_text = self._combine_pages(pages_content)

        # Calculate metadata
        total_chars = sum(page.char_count for page in pages_content)
        total_lines = sum(page.line_count for page in pages_content)
        extraction_time = time.time() - start_time

        metadata = ExtractionMetadata(
            total_pages=len(pdf_document),
            total_chars=total_chars,
            total_lines=total_lines,
            extraction_time=extraction_time,
            success_pages=len(pages_content),
            failed_pages=failed_pages,
            errors=errors,
        )

        logger.info(
            f"Extraction complete: {metadata.total_pages} pages, "
            f"{total_chars} chars, {extraction_time:.2f}s"
        )

        return full_text, metadata

    def extract_text_by_page(self, file_path: str) -> Tuple[List[PageContent], ExtractionMetadata]:
        """
        Extract text page by page

        Args:
            file_path: Path to PDF file

        Returns:
            (pages: List[PageContent], metadata: ExtractionMetadata)
        """
        import time
        start_time = time.time()

        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        pages_content = []
        errors = []
        failed_pages = 0

        try:
            pdf_document = fitz.open(file_path)

            for page_num in range(len(pdf_document)):
                try:
                    page_content = self._extract_page_text(pdf_document, page_num)
                    pages_content.append(page_content)

                except Exception as e:
                    error_msg = f"Failed to extract page {page_num + 1}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    failed_pages += 1

            pdf_document.close()

        except Exception as e:
            error_msg = f"Failed to open PDF {file_path}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        total_chars = sum(page.char_count for page in pages_content)
        total_lines = sum(page.line_count for page in pages_content)
        extraction_time = time.time() - start_time

        metadata = ExtractionMetadata(
            total_pages=len(pdf_document),
            total_chars=total_chars,
            total_lines=total_lines,
            extraction_time=extraction_time,
            success_pages=len(pages_content),
            failed_pages=failed_pages,
            errors=errors,
        )

        return pages_content, metadata

    def extract_with_coordinates(self, file_path: str) -> Tuple[List[Dict], ExtractionMetadata]:
        """
        Extract text with position coordinates

        Useful for:
        - Layout-aware chunking
        - Table detection
        - Spatial analysis

        Returns:
            (blocks: List[Dict], metadata: ExtractionMetadata)
        """
        import time
        start_time = time.time()

        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        all_blocks = []
        errors = []

        try:
            pdf_document = fitz.open(file_path)

            for page_num in range(len(pdf_document)):
                try:
                    page = pdf_document[page_num]
                    blocks = page.get_text("blocks")  # Returns layout-aware blocks

                    for block in blocks:
                        if block[6] == 0:  # Text block (not image)
                            all_blocks.append({
                                "page": page_num + 1,
                                "bbox": block[:4],  # (x0, y0, x1, y1)
                                "text": block[4],
                                "block_type": "text",
                            })

                except Exception as e:
                    error_msg = f"Failed to extract coordinates from page {page_num + 1}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

            pdf_document.close()

        except Exception as e:
            error_msg = f"Failed to open PDF {file_path}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        extraction_time = time.time() - start_time

        metadata = ExtractionMetadata(
            total_pages=len(pdf_document),
            total_chars=sum(len(b.get("text", "")) for b in all_blocks),
            total_lines=0,
            extraction_time=extraction_time,
            success_pages=len(pdf_document),
            failed_pages=len(errors),
            errors=errors,
        )

        return all_blocks, metadata

    def extract_metadata(self, file_path: str) -> Dict:
        """
        Extract PDF metadata

        Returns:
            Dictionary with metadata
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            pdf_document = fitz.open(file_path)

            metadata = pdf_document.metadata or {}
            file_info = Path(file_path).stat()

            result = {
                "title": metadata.get("title", "").strip() or None,
                "author": metadata.get("author", "").strip() or None,
                "subject": metadata.get("subject", "").strip() or None,
                "keywords": metadata.get("keywords", "").strip() or None,
                "creator": metadata.get("creator", "").strip() or None,
                "producer": metadata.get("producer", "").strip() or None,
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": len(pdf_document),
                "file_size_bytes": file_info.st_size,
                "is_encrypted": pdf_document.is_pdf and pdf_document.is_encrypted,
                "is_reflowable": pdf_document.is_reflowable,
            }

            pdf_document.close()
            logger.debug(f"Extracted metadata: {result}")

            return result

        except Exception as e:
            error_msg = f"Failed to extract metadata from {file_path}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _extract_page_text(self, pdf_document, page_num: int) -> PageContent:
        """
        Extract text from single page

        Args:
            pdf_document: Open PyMuPDF document
            page_num: Page index (0-based)

        Returns:
            PageContent object
        """
        page = pdf_document[page_num]

        # Extract text with layout preservation
        text = page.get_text(
            "text" if self.preserve_layout else "raw"
        )

        # Get text blocks for analysis
        blocks = page.get_text("blocks")

        # Count metrics
        char_count = len(text)
        line_count = text.count("\n") + 1

        logger.debug(f"Page {page_num + 1}: {char_count} chars, {line_count} lines")

        return PageContent(
            page_number=page_num + 1,
            text=text,
            blocks=blocks,
            char_count=char_count,
            line_count=line_count,
        )

    def _combine_pages(self, pages: List[PageContent]) -> str:
        """Combine multiple pages into single text"""
        combined = []
        for page in pages:
            combined.append(f"\n{'='*80}\nPage {page.page_number}\n{'='*80}\n")
            combined.append(page.text)

        return "\n".join(combined)
