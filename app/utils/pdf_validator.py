import os
from pathlib import Path
from typing import Optional, Dict
import mimetypes

class PDFValidator:
    """Validate PDF files before processing"""

    # PDF magic bytes signature
    PDF_SIGNATURE = b"%PDF"
    ALLOWED_MIME_TYPES = {"application/pdf"}
    MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

    @staticmethod
    def validate_extension(filename: str) -> bool:
        """Check if file has .pdf extension"""
        return filename.lower().endswith(".pdf")

    @staticmethod
    def validate_mime_type(file_content: bytes) -> bool:
        """Check if file starts with PDF signature"""
        return file_content.startswith(PDFValidator.PDF_SIGNATURE)

    @staticmethod
    def validate_size(file_size: int, max_size_mb: int = 100) -> bool:
        """Check if file size is within limits"""
        max_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_bytes

    @staticmethod
    def validate(filename: str, file_content: bytes, max_size_mb: int = 100) -> tuple[bool, Optional[str]]:
        """
        Validate PDF file comprehensively
        Returns: (is_valid, error_message)
        """
        # Check extension
        if not PDFValidator.validate_extension(filename):
            return False, f"Invalid file extension. Expected .pdf, got .{filename.split('.')[-1]}"

        # Check MIME type via magic bytes
        if not PDFValidator.validate_mime_type(file_content):
            return False, "File is not a valid PDF (invalid magic bytes)"

        # Check file size
        if not PDFValidator.validate_size(len(file_content), max_size_mb):
            return False, f"File too large. Maximum size: {max_size_mb}MB"

        return True, None
