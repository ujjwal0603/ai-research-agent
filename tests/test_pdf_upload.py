import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.utils import PDFValidator, PDFProcessor

@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)

@pytest.fixture
def sample_pdf():
    """Create a minimal valid PDF for testing"""
    # Minimal PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000203 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
305
%%EOF"""
    return pdf_content

class TestPDFValidator:
    """Test PDF validation"""

    def test_validate_pdf_extension(self):
        """Test PDF extension validation"""
        assert PDFValidator.validate_extension("document.pdf")
        assert PDFValidator.validate_extension("Document.PDF")
        assert not PDFValidator.validate_extension("document.txt")

    def test_validate_pdf_mime_type(self, sample_pdf):
        """Test PDF magic bytes validation"""
        assert PDFValidator.validate_mime_type(sample_pdf)
        assert not PDFValidator.validate_mime_type(b"Not a PDF")

    def test_validate_pdf_size(self):
        """Test file size validation"""
        small_file = b"x" * 1000
        large_file = b"x" * (101 * 1024 * 1024)

        assert PDFValidator.validate_size(len(small_file), 100)
        assert not PDFValidator.validate_size(len(large_file), 100)

    def test_validate_pdf_complete(self, sample_pdf):
        """Test complete PDF validation"""
        is_valid, error = PDFValidator.validate("test.pdf", sample_pdf, 100)
        assert is_valid
        assert error is None

    def test_validate_pdf_invalid_extension(self, sample_pdf):
        """Test validation fails with wrong extension"""
        is_valid, error = PDFValidator.validate("test.txt", sample_pdf, 100)
        assert not is_valid
        assert "extension" in error.lower()

    def test_validate_pdf_not_pdf_content(self):
        """Test validation fails with non-PDF content"""
        is_valid, error = PDFValidator.validate("test.pdf", b"Not a PDF", 100)
        assert not is_valid
        assert "magic bytes" in error.lower()

class TestPDFProcessor:
    """Test PDF text and metadata extraction"""

    def test_extract_metadata_invalid_file(self, tmp_path):
        """Test metadata extraction from invalid file"""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("Not a PDF")

        metadata = PDFProcessor.extract_metadata(str(invalid_pdf))
        assert metadata["page_count"] == 0

    def test_get_file_size_info(self, tmp_path, sample_pdf):
        """Test file size information retrieval"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(sample_pdf)

        size_info = PDFProcessor.get_file_size_info(str(pdf_file))
        assert size_info["bytes"] > 0
        assert size_info["kilobytes"] > 0
        assert size_info["megabytes"] >= 0

class TestPDFUploadEndpoint:
    """Test PDF upload endpoint"""

    def test_upload_pdf_success(self, client, sample_pdf):
        """Test successful PDF upload"""
        response = client.post(
            "/documents/upload/pdf",
            files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "uploaded"
        assert data["file_name"] == "test.pdf"
        assert "document_id" in data
        assert len(data["document_id"]) == 36  # UUID length

    def test_upload_pdf_detailed(self, client, sample_pdf):
        """Test detailed PDF upload endpoint"""
        response = client.post(
            "/documents/upload/pdf/detailed",
            files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "uploaded"
        assert "metadata" in data
        assert "file_info" in data
        assert "document_id" in data

    def test_upload_pdf_no_file(self, client):
        """Test upload without file"""
        response = client.post("/documents/upload/pdf", files={})
        assert response.status_code != 200

    def test_upload_pdf_invalid_format(self, client):
        """Test upload with non-PDF file"""
        invalid_content = b"This is not a PDF"
        response = client.post(
            "/documents/upload/pdf",
            files={"file": ("test.pdf", io.BytesIO(invalid_content), "application/pdf")},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_validate_pdf_endpoint(self, client, sample_pdf):
        """Test PDF validation endpoint"""
        response = client.post(
            "/documents/validate/pdf",
            files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"]
        assert data["file_name"] == "test.pdf"
        assert data["file_size"] > 0

    def test_validate_pdf_invalid_endpoint(self, client):
        """Test PDF validation with invalid file"""
        invalid_content = b"Not a PDF"
        response = client.post(
            "/documents/validate/pdf",
            files={"file": ("test.pdf", io.BytesIO(invalid_content), "application/pdf")},
        )

        assert response.status_code == 400
        data = response.json()
        assert not data["is_valid"]
        assert data["error"] is not None
