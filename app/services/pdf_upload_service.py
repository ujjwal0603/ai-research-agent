from typing import Dict, Optional, Tuple
import uuid
from app.services.upload_service import UploadService
from app.utils import setup_logger

logger = setup_logger(__name__)

class PDFUploadService:
    """
    Orchestrate PDF upload workflow
    Handles: validation → storage → extraction → metadata generation
    """

    def __init__(self, upload_service: UploadService):
        self.upload_service = upload_service

    async def process_pdf_upload(
        self, filename: str, file_content: bytes
    ) -> Tuple[bool, Dict]:
        """
        Process PDF upload end-to-end
        Returns: (success, response_dict)
        """
        document_id = str(uuid.uuid4())

        try:
            # Step 1: Validate PDF
            logger.info(f"Validating PDF: {filename}")
            is_valid, error_msg = self.upload_service.validate_pdf(filename, file_content)

            if not is_valid:
                logger.warning(f"PDF validation failed: {error_msg}")
                return False, {
                    "document_id": document_id,
                    "file_name": filename,
                    "status": "validation_failed",
                    "error": error_msg,
                }

            # Step 2: Save file to disk
            logger.info(f"Saving PDF file: {filename}")
            file_path = self.upload_service.save_file(document_id, filename, file_content)

            # Step 3: Extract metadata
            logger.info(f"Extracting metadata from: {filename}")
            metadata = self.upload_service.extract_pdf_metadata(file_path)

            # Step 4: Extract text (for embeddings)
            logger.info(f"Extracting text from: {filename}")
            text_content = self.upload_service.extract_pdf_text(file_path)

            # Step 5: Get file info
            file_info = self.upload_service.get_file_info(file_path)

            logger.info(f"PDF upload completed successfully: {document_id}")

            return True, {
                "document_id": document_id,
                "file_name": filename,
                "status": "uploaded",
                "file_path": file_path,
                "metadata": metadata,
                "text_preview": text_content[:500] if text_content else None,
                "file_info": file_info,
                "message": f"Successfully uploaded {filename} ({metadata.get('page_count', 0)} pages)",
            }

        except Exception as e:
            logger.error(f"PDF upload processing failed: {str(e)}", exc_info=True)
            return False, {
                "document_id": document_id,
                "file_name": filename,
                "status": "processing_failed",
                "error": str(e),
            }

    async def validate_pdf_only(self, filename: str, file_content: bytes) -> Tuple[bool, Optional[str]]:
        """Quick validation without storage"""
        logger.debug(f"Quick validating PDF: {filename}")
        return self.upload_service.validate_pdf(filename, file_content)
