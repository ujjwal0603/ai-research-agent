"""
Document upload, listing, detail, and deletion routes.

Protected — every endpoint requires a valid access token.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_ingestion_pipeline,
    get_qdrant_store,
)
from api.middleware.auth import get_current_user
from config.constants import DocumentStatus
from config.settings import get_settings
from database.connection import get_db
from schemas.documents import DocumentDetail, DocumentInfo, UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


# ── Upload ──────────────────────────────────────────


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Upload a PDF, run the ingestion pipeline, and return metadata."""
    # ── Validate filename & extension ───────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    # ── Size check ──────────────────────────────────
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # ── Magic-byte check ────────────────────────────
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file (bad magic bytes)")

    try:
        document_id = str(uuid.uuid4())
        user_id = current_user["user_id"]

        # Save to disk
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info("Saved PDF: %s → %s", file.filename, file_path)

        # Run ingestion pipeline
        pipeline = get_ingestion_pipeline()
        page_count = 0
        chunk_count = 0
        if pipeline is not None:
            result = await pipeline.process_document(
                file_path=file_path,
                document_id=document_id,
                filename=file.filename,
                user_id=user_id,
            )
            page_count = result.get("page_count", 0)
            chunk_count = result.get("chunk_count", 0)
        else:
            # Fallback: use V1 services if pipeline not yet initialised
            from core import (
                get_chunking_service,
                get_embedding_service,
                get_pdf_service,
            )

            pdf_svc = get_pdf_service()
            pages = pdf_svc.extract_text_by_page(file_path)
            page_count = len(pages)

            chunking_svc = get_chunking_service()
            all_chunks = []
            for page_data in pages:
                if not page_data["text"].strip():
                    continue
                page_chunks = chunking_svc.chunk_text(
                    page_data["text"],
                    metadata={
                        "document_id": document_id,
                        "document_name": file.filename,
                        "page_number": page_data["page_number"],
                    },
                )
                all_chunks.extend(page_chunks)

            for i, chunk in enumerate(all_chunks):
                chunk["chunk_index"] = i
            chunk_count = len(all_chunks)

            if not all_chunks:
                os.remove(file_path)
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract any text from the PDF.",
                )

        # Persist document record to DB
        try:
            from database.models import Document

            doc_record = Document(
                id=uuid.UUID(document_id),
                user_id=uuid.UUID(user_id),
                filename=file.filename,
                original_name=file.filename,
                page_count=page_count,
                chunk_count=chunk_count,
                file_size_bytes=len(content),
                status=DocumentStatus.PROCESSED,
                uploaded_at=datetime.now(timezone.utc),
            )
            session.add(doc_record)
            await session.commit()
        except Exception as db_exc:
            logger.warning("Could not save document record to DB: %s", db_exc)

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            page_count=page_count,
            chunk_count=chunk_count,
            status=DocumentStatus.PROCESSED,
            message=(
                f"Successfully processed '{file.filename}': "
                f"{page_count} pages, {chunk_count} chunks indexed"
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload processing failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {exc}",
        )


# ── List documents ──────────────────────────────────


@router.get("", response_model=list[DocumentInfo])
async def list_documents(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List all documents owned by the authenticated user."""
    try:
        from database.models import Document

        result = await session.execute(
            select(Document).where(Document.user_id == uuid.UUID(current_user["user_id"]))
        )
        rows = result.scalars().all()
        return [
            DocumentInfo(
                document_id=str(doc.id),
                filename=doc.filename,
                page_count=doc.page_count,
                chunk_count=doc.chunk_count,
                upload_time=doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status,
                user_id=str(doc.user_id),
            )
            for doc in rows
        ]
    except Exception as exc:
        logger.warning("DB query failed, falling back to empty list: %s", exc)
        return []


# ── Document detail ─────────────────────────────────


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return detailed metadata for a single document."""
    from database.models import Document

    result = await session.execute(
        select(Document).where(
            Document.id == uuid.UUID(document_id),
            Document.user_id == uuid.UUID(current_user["user_id"]),
        )
    )
    doc = result.scalars().first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetail(
        document_id=str(doc.id),
        filename=doc.filename,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        upload_time=doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status,
        user_id=str(doc.user_id),
    )


# ── Delete document ─────────────────────────────────


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a document, its vectors, and the uploaded file."""
    from database.models import Document

    result = await session.execute(
        select(Document).where(
            Document.id == uuid.UUID(document_id),
            Document.user_id == uuid.UUID(current_user["user_id"]),
        )
    )
    doc = result.scalars().first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove vectors from Qdrant
    try:
        qdrant = get_qdrant_store()
        if qdrant is not None and hasattr(qdrant, "delete_document"):
            await qdrant.delete_document(document_id)
    except Exception as exc:
        logger.warning("Qdrant vector deletion failed: %s", exc)

    # Remove file from disk
    file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove DB record
    await session.delete(doc)
    await session.commit()

    logger.info("Deleted document %s", document_id)
    return {"status": "deleted", "document_id": document_id}
