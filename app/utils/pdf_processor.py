from pathlib import Path
from typing import Optional, Dict, List
import PyPDF2
from app.utils import setup_logger

logger = setup_logger(__name__)

class PDFProcessor:
    """Extract text and metadata from PDF files"""

    @staticmethod
    def extract_metadata(file_path: str) -> Dict:
        """Extract PDF metadata (title, author, pages, etc.)"""
        try:
            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                metadata = reader.metadata or {}

                return {
                    "page_count": len(reader.pages),
                    "title": metadata.get("/Title", "").strip() or None,
                    "author": metadata.get("/Author", "").strip() or None,
                    "subject": metadata.get("/Subject", "").strip() or None,
                    "creator": metadata.get("/Creator", "").strip() or None,
                    "producer": metadata.get("/Producer", "").strip() or None,
                    "creation_date": str(metadata.get("/CreationDate", "")) if metadata.get("/CreationDate") else None,
                    "modification_date": str(metadata.get("/ModDate", "")) if metadata.get("/ModDate") else None,
                }
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {str(e)}")
            return {"page_count": 0}

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract all text from PDF file"""
        try:
            text_content = []

            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)

                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(f"--- Page {page_num + 1} ---\n{text}")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")

            extracted_text = "\n\n".join(text_content)
            logger.debug(f"Extracted {len(extracted_text)} characters from {file_path}")

            return extracted_text

        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {str(e)}")
            return ""

    @staticmethod
    def extract_text_by_page(file_path: str) -> List[str]:
        """Extract text page by page from PDF"""
        try:
            pages = []

            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)

                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        pages.append(text or "")
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {str(e)}")
                        pages.append("")

            return pages

        except Exception as e:
            logger.error(f"Failed to extract pages from {file_path}: {str(e)}")
            return []

    @staticmethod
    def get_file_size_info(file_path: str) -> Dict:
        """Get file size information"""
        try:
            file_size = Path(file_path).stat().st_size
            return {
                "bytes": file_size,
                "kilobytes": round(file_size / 1024, 2),
                "megabytes": round(file_size / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {str(e)}")
            return {"bytes": 0, "kilobytes": 0, "megabytes": 0}
