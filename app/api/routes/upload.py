from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.models import UploadResponse
from app.services import UploadService, PDFUploadService
from app.config import get_settings
from app.utils import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

def get_upload_service() -> UploadService:
    """Dependency: Initialize upload service"""
    settings = get_settings()
    return UploadService(settings.UPLOAD_DIR, settings.ALLOWED_EXTENSIONS, settings.MAX_UPLOAD_SIZE_MB)

def get_pdf_upload_service(upload_service: UploadService = Depends(get_upload_service)) -> PDFUploadService:
    """Dependency: Initialize PDF upload service"""
    return PDFUploadService(upload_service)

@router.post("/upload/pdf", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    pdf_upload_service: PDFUploadService = Depends(get_pdf_upload_service),
):
    """
    Upload and process a PDF file

    Returns detailed metadata and validation status
    """
    try:
        logger.info(f"Received PDF upload: {file.filename}")

        # Validate file is present
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Read file content
        try:
            content = await file.read()
        except Exception as e:
            logger.error(f"Failed to read file: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to read file")

        # Check if file is empty
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        # Process PDF upload
        success, response_data = await pdf_upload_service.process_pdf_upload(file.filename, content)

        if not success:
            logger.warning(f"PDF upload validation failed for {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=response_data.get("error", "PDF upload validation failed"),
            )

        # Extract data for response
        document_id = response_data["document_id"]
        metadata = response_data.get("metadata", {})
        file_info = response_data.get("file_info", {})

        # Create standard response
        response = UploadResponse(
            document_id=document_id,
            file_name=file.filename,
            status="uploaded",
            chunks_created=metadata.get("page_count", 0),
            message=response_data.get("message", f"Successfully uploaded {file.filename}"),
        )

        logger.info(f"PDF upload completed: {document_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during PDF upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="PDF upload processing failed")

@router.post("/upload/pdf/detailed")
async def upload_pdf_detailed(
    file: UploadFile = File(...),
    pdf_upload_service: PDFUploadService = Depends(get_pdf_upload_service),
):
    """
    Upload PDF and return detailed metadata

    Includes page count, author, text preview, file size, etc.
    """
    try:
        logger.info(f"Received detailed PDF upload request: {file.filename}")

        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        success, response_data = await pdf_upload_service.process_pdf_upload(file.filename, content)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=response_data.get("error", "PDF upload failed"),
            )

        # Return full detailed response
        return JSONResponse(
            status_code=200,
            content={
                "document_id": response_data["document_id"],
                "file_name": response_data["file_name"],
                "status": response_data["status"],
                "message": response_data.get("message"),
                "metadata": response_data.get("metadata", {}),
                "file_info": response_data.get("file_info", {}),
                "text_preview": response_data.get("text_preview"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in detailed PDF upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process PDF")

@router.post("/validate/pdf")
async def validate_pdf(
    file: UploadFile = File(...),
    pdf_upload_service: PDFUploadService = Depends(get_pdf_upload_service),
):
    """
    Validate PDF without storing it

    Useful for checking file integrity before actual upload
    """
    try:
        logger.debug(f"Validating PDF: {file.filename}")

        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        is_valid, error_msg = await pdf_upload_service.validate_pdf_only(file.filename, content)

        return {
            "file_name": file.filename,
            "is_valid": is_valid,
            "file_size": len(content),
            "size_mb": round(len(content) / (1024 * 1024), 2),
            "error": error_msg if not is_valid else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Validation failed")

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get document metadata"""
    logger.info(f"Fetching document metadata: {document_id}")
    # Placeholder: Implement document retrieval from database
    return {
        "document_id": document_id,
        "status": "indexed",
        "chunks": 0,
    }

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete document and its embeddings"""
    logger.info(f"Deleting document: {document_id}")
    # Placeholder: Implement document deletion
    return {"status": "deleted", "document_id": document_id}
