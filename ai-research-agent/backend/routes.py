from fastapi import APIRouter, UploadFile, File, HTTPException
from file_service import FileService
from utils import validate_pdf
from schemas import UploadResponse

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a PDF file.

    Args:
        file: PDF file to upload

    Returns:
        UploadResponse with file metadata

    Raises:
        HTTPException 400: Invalid file (wrong type, size, or extension)
        HTTPException 500: Server error during file save
    """
    # Read file content
    content = await file.read()

    # Validate PDF
    is_valid, error_message = validate_pdf(
        filename=file.filename,
        mime_type=file.content_type,
        file_size=len(content),
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    try:
        # Save file and return response
        response = await FileService.save_pdf(content, file.filename)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}",
        )
