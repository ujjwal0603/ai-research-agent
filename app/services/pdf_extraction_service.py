from typing import Dict, List, Optional, Tuple
from app.utils import setup_logger
from app.utils.pdf_extractor import PDFExtractor, PageContent, ExtractionMetadata

logger = setup_logger(__name__)

class PDFExtractionService:
    """
    High-level PDF text extraction service

    Provides:
    - Unified extraction interface
    - Error handling and recovery
    - Caching for repeated documents
    - Format conversion
    - Validation
    """

    def __init__(self, preserve_layout: bool = True, max_extraction_time: float = 300.0):
        """
        Initialize extraction service

        Args:
            preserve_layout: Preserve PDF layout in extracted text
            max_extraction_time: Maximum time (seconds) for extraction
        """
        self.extractor = PDFExtractor(preserve_layout=preserve_layout)
        self.max_extraction_time = max_extraction_time
        self._extraction_cache = {}
        logger.info(f"PDFExtractionService initialized")

    def extract_full_text(self, file_path: str, use_cache: bool = False) -> Dict:
        """
        Extract complete text from PDF

        Args:
            file_path: Path to PDF file
            use_cache: Use cached result if available

        Returns:
            {
                "success": bool,
                "text": str,
                "metadata": ExtractionMetadata,
                "error": Optional[str]
            }
        """
        # Check cache
        if use_cache and file_path in self._extraction_cache:
            logger.debug(f"Using cached extraction for {file_path}")
            return self._extraction_cache[file_path]

        try:
            logger.info(f"Extracting full text from: {file_path}")

            text, metadata = self.extractor.extract_text(file_path)

            # Check extraction time
            if metadata.extraction_time > self.max_extraction_time:
                logger.warning(
                    f"Extraction took {metadata.extraction_time:.2f}s (exceeds {self.max_extraction_time}s)"
                )

            result = {
                "success": True,
                "text": text,
                "metadata": {
                    "total_pages": metadata.total_pages,
                    "total_chars": metadata.total_chars,
                    "total_lines": metadata.total_lines,
                    "extraction_time": metadata.extraction_time,
                    "success_pages": metadata.success_pages,
                    "failed_pages": metadata.failed_pages,
                    "errors": metadata.errors,
                },
                "error": None,
            }

            # Cache result
            if use_cache:
                self._extraction_cache[file_path] = result

            logger.info(f"Full text extraction successful: {metadata.total_chars} chars")
            return result

        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "text": None,
                "metadata": None,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = f"Extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "text": None,
                "metadata": None,
                "error": error_msg,
            }

    def extract_pages(
        self, file_path: str, page_range: Optional[Tuple[int, int]] = None
    ) -> Dict:
        """
        Extract text organized by pages

        Args:
            file_path: Path to PDF file
            page_range: (start_page, end_page) 1-indexed, inclusive

        Returns:
            {
                "success": bool,
                "pages": List[{"page": int, "text": str, "char_count": int}],
                "metadata": ExtractionMetadata,
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"Extracting pages from: {file_path}")

            pages, metadata = self.extractor.extract_text_by_page(file_path)

            # Apply page range filter
            if page_range:
                start, end = page_range
                pages = [p for p in pages if start <= p.page_number <= end]
                logger.debug(f"Filtered to pages {start}-{end}")

            page_data = [
                {
                    "page": p.page_number,
                    "text": p.text,
                    "char_count": p.char_count,
                    "line_count": p.line_count,
                }
                for p in pages
            ]

            result = {
                "success": True,
                "pages": page_data,
                "metadata": {
                    "total_pages": metadata.total_pages,
                    "extracted_pages": len(page_data),
                    "total_chars": metadata.total_chars,
                    "extraction_time": metadata.extraction_time,
                    "errors": metadata.errors,
                },
                "error": None,
            }

            logger.info(f"Page extraction successful: {len(page_data)} pages")
            return result

        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "pages": None,
                "metadata": None,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = f"Page extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "pages": None,
                "metadata": None,
                "error": error_msg,
            }

    def extract_with_layout(self, file_path: str) -> Dict:
        """
        Extract text with spatial coordinates

        Useful for:
        - Table extraction
        - Layout-aware chunking
        - Document structure analysis

        Returns:
            {
                "success": bool,
                "blocks": List[{"page": int, "bbox": tuple, "text": str}],
                "metadata": ExtractionMetadata,
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"Extracting with layout from: {file_path}")

            blocks, metadata = self.extractor.extract_with_coordinates(file_path)

            result = {
                "success": True,
                "blocks": blocks,
                "metadata": {
                    "total_pages": metadata.total_pages,
                    "total_blocks": len(blocks),
                    "total_chars": metadata.total_chars,
                    "extraction_time": metadata.extraction_time,
                    "errors": metadata.errors,
                },
                "error": None,
            }

            logger.info(f"Layout extraction successful: {len(blocks)} blocks")
            return result

        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "blocks": None,
                "metadata": None,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = f"Layout extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "blocks": None,
                "metadata": None,
                "error": error_msg,
            }

    def extract_metadata(self, file_path: str) -> Dict:
        """
        Extract PDF metadata only

        Returns:
            {
                "success": bool,
                "metadata": Dict,
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"Extracting metadata from: {file_path}")

            metadata = self.extractor.extract_metadata(file_path)

            result = {
                "success": True,
                "metadata": metadata,
                "error": None,
            }

            logger.info(f"Metadata extraction successful")
            return result

        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "metadata": None,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = f"Metadata extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "metadata": None,
                "error": error_msg,
            }

    def extract_text_snippet(self, file_path: str, page: int, max_chars: int = 500) -> str:
        """
        Extract text snippet from specific page

        Useful for:
        - Previews
        - Summaries
        - Quick validation

        Args:
            file_path: Path to PDF file
            page: Page number (1-indexed)
            max_chars: Maximum characters to extract

        Returns:
            Text snippet (truncated)
        """
        try:
            pages, _ = self.extractor.extract_text_by_page(file_path)

            # Find requested page
            target_page = next((p for p in pages if p.page_number == page), None)

            if not target_page:
                logger.warning(f"Page {page} not found in {file_path}")
                return ""

            # Return snippet
            snippet = target_page.text[:max_chars]
            if len(target_page.text) > max_chars:
                snippet += "..."

            logger.debug(f"Extracted snippet from page {page}")
            return snippet

        except Exception as e:
            logger.error(f"Snippet extraction failed: {str(e)}")
            return ""

    def clear_cache(self):
        """Clear extraction cache"""
        cache_size = len(self._extraction_cache)
        self._extraction_cache.clear()
        logger.info(f"Cleared extraction cache ({cache_size} items)")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "cached_files": len(self._extraction_cache),
            "total_size_bytes": sum(
                len(v.get("text", "")) for v in self._extraction_cache.values()
            ),
        }
