"""
PDF upload and document management endpoints.

Upload pipeline:
  1. Validate file (type, size, magic bytes)
  2. Save PDF to disk
  3. Extract text using PyMuPDF (page-by-page)
  4. Chunk text into semantic pieces
  5. Generate embeddings using sentence-transformers
  6. Store vectors + metadata in FAISS
"""

import os
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from config.settings import get_settings
from models.schemas import UploadResponse, DocumentInfo
from core import (
    get_pdf_service,
    get_chunking_service,
    get_embedding_service,
    get_faiss_store,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and process it through the full RAG pipeline.

    Returns document ID, page count, and number of chunks indexed.
    """
    # ── Validation ──────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file (bad magic bytes)")

    # ── Processing ──────────────────────────────────
    try:
        document_id = str(uuid.uuid4())

        # Save file to disk
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"Saved PDF: {file.filename} → {file_path}")

        # Extract text page-by-page
        pdf_service = get_pdf_service()
        pages = pdf_service.extract_text_by_page(file_path)
        page_count = len(pages)

        # Chunk text with page number tracking
        chunking_service = get_chunking_service()
        all_chunks = []

        for page_data in pages:
            if not page_data["text"].strip():
                continue

            page_chunks = chunking_service.chunk_text(
                page_data["text"],
                metadata={
                    "document_id": document_id,
                    "document_name": file.filename,
                    "page_number": page_data["page_number"],
                },
            )
            all_chunks.extend(page_chunks)

        # Re-index chunks sequentially
        for i, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = i

        if not all_chunks:
            # Clean up saved file
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Could not extract any text from the PDF. It may be scanned/image-based.",
            )

        # Generate embeddings
        embedding_service = get_embedding_service()
        chunk_texts = [c["text"] for c in all_chunks]
        embeddings = embedding_service.embed_texts(chunk_texts)

        # Store in FAISS
        faiss_store = get_faiss_store()
        faiss_store.add_document(
            document_id=document_id,
            filename=file.filename,
            chunks=all_chunks,
            embeddings=embeddings,
            page_count=page_count,
            file_size_bytes=len(content),
        )

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            page_count=page_count,
            chunk_count=len(all_chunks),
            status="processed",
            message=f"Successfully processed '{file.filename}': {page_count} pages, {len(all_chunks)} chunks indexed",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """List all uploaded and processed documents"""
    faiss_store = get_faiss_store()
    docs = faiss_store.list_documents()
    return [DocumentInfo(**doc) for doc in docs]


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document, its vectors, and the uploaded file"""
    faiss_store = get_faiss_store()

    doc = faiss_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    faiss_store.delete_document(document_id)

    # Remove file from disk
    file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"status": "deleted", "document_id": document_id}
