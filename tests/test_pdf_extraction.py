import pytest
import fitz
from pathlib import Path
from app.utils import PDFExtractor, PageContent, ExtractionMetadata
from app.services import PDFExtractionService

@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a test PDF file with multiple pages"""
    pdf_path = tmp_path / "test.pdf"

    # Create a PDF with PyMuPDF
    doc = fitz.open()

    # Add 3 pages
    for page_num in range(3):
        page = doc.new_page()
        text = f"Page {page_num + 1}\n\nThis is test content on page {page_num + 1}.\n" * 5
        page.insert_text((50, 50), text, fontsize=12)

    doc.save(str(pdf_path))
    doc.close()

    return str(pdf_path)

@pytest.fixture
def extractor():
    """Create PDFExtractor instance"""
    return PDFExtractor(preserve_layout=True)

@pytest.fixture
def extraction_service():
    """Create PDFExtractionService instance"""
    return PDFExtractionService(preserve_layout=True, max_extraction_time=300)

class TestPDFExtractor:
    """Test PDFExtractor class"""

    def test_extract_text(self, extractor, sample_pdf_file):
        """Test basic text extraction"""
        text, metadata = extractor.extract_text(sample_pdf_file)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "Page 1" in text
        assert "Page 2" in text
        assert "Page 3" in text

    def test_extract_text_metadata(self, extractor, sample_pdf_file):
        """Test extraction metadata"""
        text, metadata = extractor.extract_text(sample_pdf_file)

        assert isinstance(metadata, ExtractionMetadata)
        assert metadata.total_pages == 3
        assert metadata.success_pages == 3
        assert metadata.failed_pages == 0
        assert metadata.total_chars > 0
        assert metadata.extraction_time > 0

    def test_extract_text_by_page(self, extractor, sample_pdf_file):
        """Test page-by-page extraction"""
        pages, metadata = extractor.extract_text_by_page(sample_pdf_file)

        assert len(pages) == 3
        assert all(isinstance(p, PageContent) for p in pages)
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert pages[2].page_number == 3

    def test_extract_page_content(self, extractor, sample_pdf_file):
        """Test PageContent properties"""
        pages, _ = extractor.extract_text_by_page(sample_pdf_file)
        page = pages[0]

        assert isinstance(page.page_number, int)
        assert isinstance(page.text, str)
        assert isinstance(page.blocks, list)
        assert isinstance(page.char_count, int)
        assert isinstance(page.line_count, int)
        assert page.char_count > 0

    def test_extract_metadata(self, extractor, sample_pdf_file):
        """Test metadata extraction"""
        metadata = extractor.extract_metadata(sample_pdf_file)

        assert isinstance(metadata, dict)
        assert "page_count" in metadata
        assert "file_size_bytes" in metadata
        assert "is_encrypted" in metadata
        assert metadata["page_count"] == 3

    def test_extract_with_coordinates(self, extractor, sample_pdf_file):
        """Test extraction with spatial coordinates"""
        blocks, metadata = extractor.extract_with_coordinates(sample_pdf_file)

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert all("page" in b for b in blocks)
        assert all("bbox" in b for b in blocks)
        assert all("text" in b for b in blocks)

    def test_extract_nonexistent_file(self, extractor):
        """Test extraction of non-existent file"""
        with pytest.raises(FileNotFoundError):
            extractor.extract_text("/nonexistent/path.pdf")

    def test_extract_invalid_pdf(self, extractor, tmp_path):
        """Test extraction of invalid PDF"""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("Not a real PDF")

        with pytest.raises(Exception):
            extractor.extract_text(str(invalid_pdf))

class TestPDFExtractionService:
    """Test PDFExtractionService class"""

    def test_extract_full_text_success(self, extraction_service, sample_pdf_file):
        """Test successful full text extraction"""
        result = extraction_service.extract_full_text(sample_pdf_file)

        assert result["success"] is True
        assert result["text"] is not None
        assert len(result["text"]) > 0
        assert result["error"] is None
        assert result["metadata"]["total_pages"] == 3

    def test_extract_full_text_error(self, extraction_service):
        """Test full text extraction error handling"""
        result = extraction_service.extract_full_text("/nonexistent.pdf")

        assert result["success"] is False
        assert result["text"] is None
        assert result["error"] is not None

    def test_extract_pages(self, extraction_service, sample_pdf_file):
        """Test page-by-page extraction"""
        result = extraction_service.extract_pages(sample_pdf_file)

        assert result["success"] is True
        assert len(result["pages"]) == 3
        assert all("page" in p for p in result["pages"])
        assert all("text" in p for p in result["pages"])
        assert all("char_count" in p for p in result["pages"])

    def test_extract_pages_with_range(self, extraction_service, sample_pdf_file):
        """Test page extraction with range filter"""
        result = extraction_service.extract_pages(sample_pdf_file, page_range=(1, 2))

        assert result["success"] is True
        assert len(result["pages"]) == 2
        assert result["pages"][0]["page"] == 1
        assert result["pages"][1]["page"] == 2

    def test_extract_with_layout(self, extraction_service, sample_pdf_file):
        """Test layout-aware extraction"""
        result = extraction_service.extract_with_layout(sample_pdf_file)

        assert result["success"] is True
        assert len(result["blocks"]) > 0
        assert all("bbox" in b for b in result["blocks"])
        assert all("text" in b for b in result["blocks"])

    def test_extract_metadata_only(self, extraction_service, sample_pdf_file):
        """Test metadata extraction"""
        result = extraction_service.extract_metadata(sample_pdf_file)

        assert result["success"] is True
        assert result["metadata"] is not None
        assert result["metadata"]["page_count"] == 3
        assert "file_size_bytes" in result["metadata"]

    def test_extract_text_snippet(self, extraction_service, sample_pdf_file):
        """Test text snippet extraction"""
        snippet = extraction_service.extract_text_snippet(sample_pdf_file, page=1, max_chars=100)

        assert isinstance(snippet, str)
        assert len(snippet) <= 103  # 100 + "..."

    def test_extract_text_snippet_invalid_page(self, extraction_service, sample_pdf_file):
        """Test snippet extraction from invalid page"""
        snippet = extraction_service.extract_text_snippet(sample_pdf_file, page=999)

        assert isinstance(snippet, str)
        assert len(snippet) == 0

    def test_caching(self, extraction_service, sample_pdf_file):
        """Test extraction caching"""
        # Extract without cache
        result1 = extraction_service.extract_full_text(sample_pdf_file, use_cache=True)
        assert result1["success"] is True

        # Extract with cache (should be instant)
        result2 = extraction_service.extract_full_text(sample_pdf_file, use_cache=True)
        assert result2["success"] is True
        assert result1["text"] == result2["text"]

        # Check cache stats
        stats = extraction_service.get_cache_stats()
        assert stats["cached_files"] == 1
        assert stats["total_size_bytes"] > 0

    def test_clear_cache(self, extraction_service, sample_pdf_file):
        """Test cache clearing"""
        extraction_service.extract_full_text(sample_pdf_file, use_cache=True)
        stats_before = extraction_service.get_cache_stats()
        assert stats_before["cached_files"] == 1

        extraction_service.clear_cache()
        stats_after = extraction_service.get_cache_stats()
        assert stats_after["cached_files"] == 0

    def test_error_handling_nonexistent(self, extraction_service):
        """Test comprehensive error handling"""
        result = extraction_service.extract_full_text("/nonexistent/path.pdf")

        assert result["success"] is False
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

class TestExtractionFlow:
    """Test complete extraction workflows"""

    def test_full_workflow(self, extraction_service, sample_pdf_file):
        """Test complete extraction workflow"""
        # Extract metadata
        meta_result = extraction_service.extract_metadata(sample_pdf_file)
        assert meta_result["success"]
        page_count = meta_result["metadata"]["page_count"]

        # Extract all text
        text_result = extraction_service.extract_full_text(sample_pdf_file)
        assert text_result["success"]
        assert text_result["metadata"]["total_pages"] == page_count

        # Extract by pages
        pages_result = extraction_service.extract_pages(sample_pdf_file)
        assert pages_result["success"]
        assert len(pages_result["pages"]) == page_count

        # Extract with layout
        layout_result = extraction_service.extract_with_layout(sample_pdf_file)
        assert layout_result["success"]

        # Get snippets
        for i in range(1, page_count + 1):
            snippet = extraction_service.extract_text_snippet(sample_pdf_file, page=i)
            assert len(snippet) > 0

    def test_error_recovery(self, extraction_service, sample_pdf_file):
        """Test graceful error recovery"""
        # Should not raise, but return success=False
        result1 = extraction_service.extract_full_text("/invalid.pdf")
        assert result1["success"] is False

        # Should still work for valid file
        result2 = extraction_service.extract_full_text(sample_pdf_file)
        assert result2["success"] is True
