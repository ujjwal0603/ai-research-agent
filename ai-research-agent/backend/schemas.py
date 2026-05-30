from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UploadResponse(BaseModel):
    """Response model for successful file upload"""
    filename: str
    file_size: int
    mime_type: str
    upload_timestamp: datetime
    file_path: str


class ErrorResponse(BaseModel):
    """Response model for error cases"""
    error: str
    detail: Optional[str] = None
    status_code: int
