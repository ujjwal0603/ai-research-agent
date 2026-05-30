import aiofiles
import uuid
from pathlib import Path
from datetime import datetime
from config import UPLOAD_DIR
from schemas import UploadResponse


class FileService:
    """Service for handling file operations"""

    @staticmethod
    async def save_pdf(file_content: bytes, filename: str) -> UploadResponse:
        """
        Save uploaded PDF to disk with unique filename.

        Args:
            file_content: Raw file bytes
            filename: Original filename

        Returns:
            UploadResponse with file metadata
        """
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return UploadResponse(
            filename=filename,
            file_size=len(file_content),
            mime_type="application/pdf",
            upload_timestamp=datetime.utcnow(),
            file_path=str(file_path),
        )
