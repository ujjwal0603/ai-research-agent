from typing import Optional, List, Dict
from pathlib import Path
from app.models import UploadResponse
from app.utils import setup_logger, PDFValidator, PDFProcessor

logger = setup_logger(__name__)

class UploadService:
    """Handle file uploads and storage"""

    def __init__(self, upload_dir: str, allowed_extensions: str, max_size_mb: int = 100):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_extensions = set(allowed_extensions.split(","))
        self.max_size_mb = max_size_mb
        logger.info(f"UploadService initialized with directory: {self.upload_dir}")

    def validate_pdf(self, filename: str, file_content: bytes) -> tuple[bool, Optional[str]]:
        """Validate PDF file"""
        is_valid, error_msg = PDFValidator.validate(filename, file_content, self.max_size_mb)
        if not is_valid:
            logger.warning(f"PDF validation failed for {filename}: {error_msg}")
        return is_valid, error_msg

    def save_file(self, document_id: str, filename: str, content: bytes) -> str:
        """Save uploaded file to disk"""
        # Create unique filename with document ID
        file_path = self.upload_dir / f"{document_id}_{filename}"

        try:
            file_path.write_bytes(content)
            logger.info(f"File saved successfully: {file_path} ({len(content)} bytes)")
            return str(file_path)
        except IOError as e:
            logger.error(f"Failed to save file {file_path}: {str(e)}")
            raise

    def extract_pdf_metadata(self, file_path: str) -> Dict:
        """Extract metadata from PDF"""
        metadata = PDFProcessor.extract_metadata(file_path)
        logger.debug(f"Extracted metadata from {file_path}: {metadata}")
        return metadata

    def extract_pdf_text(self, file_path: str) -> str:
        """Extract text content from PDF"""
        text = PDFProcessor.extract_text(file_path)
        logger.debug(f"Extracted {len(text)} characters from {file_path}")
        return text

    def get_file_info(self, file_path: str) -> Dict:
        """Get file information"""
        size_info = PDFProcessor.get_file_size_info(file_path)
        file_path_obj = Path(file_path)

        return {
            "path": str(file_path),
            "filename": file_path_obj.name,
            "size": size_info,
            "exists": file_path_obj.exists(),
        }

    def create_upload_response(
        self,
        document_id: str,
        filename: str,
        chunks_created: int,
        metadata: Optional[Dict] = None,
        file_path: Optional[str] = None,
    ) -> UploadResponse:
        """Create standardized upload response"""
        message = f"Successfully uploaded {filename}"
        if metadata and metadata.get("page_count"):
            message += f" ({metadata['page_count']} pages)"
        if chunks_created > 0:
            message += f" with {chunks_created} chunks"

        return UploadResponse(
            document_id=document_id,
            file_name=filename,
            status="uploaded",
            chunks_created=chunks_created,
            message=message,
        )
