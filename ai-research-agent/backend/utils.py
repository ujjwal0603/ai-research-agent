from pathlib import Path
from config import ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES, MAX_FILE_SIZE


def validate_file_extension(filename: str) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def validate_mime_type(mime_type: str) -> bool:
    """Check if MIME type is allowed"""
    return mime_type in ALLOWED_MIME_TYPES


def validate_file_size(file_size: int) -> bool:
    """Check if file size is within limits"""
    return file_size <= MAX_FILE_SIZE


def validate_pdf(filename: str, mime_type: str, file_size: int) -> tuple[bool, str]:
    """
    Validate PDF file comprehensively.
    Returns (is_valid, error_message)
    """
    if not validate_file_extension(filename):
        return False, "File must have .pdf extension"

    if not validate_mime_type(mime_type):
        return False, "File must be a PDF (application/pdf)"

    if not validate_file_size(file_size):
        return False, f"File size exceeds maximum limit of {MAX_FILE_SIZE / (1024*1024):.1f} MB"

    return True, ""
