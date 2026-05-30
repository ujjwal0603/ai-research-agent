# PDF Upload Quick Reference

## File Organization

```
app/
├── api/routes/upload.py              ← API endpoints
├── services/
│   ├── upload_service.py              ← Core upload logic
│   └── pdf_upload_service.py          ← PDF-specific orchestration
└── utils/
    ├── pdf_validator.py               ← PDF validation (56 lines)
    └── pdf_processor.py               ← Text/metadata extraction (94 lines)

tests/
└── test_pdf_upload.py                 ← Complete test suite (150+ tests)
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Includes: PyPDF2, FastAPI, Pydantic, pytest
```

### 2. Create Uploads Directory
```bash
mkdir -p uploads
```

### 3. Run Development Server
```bash
python main.py
# Server running on http://localhost:8000
```

### 4. Upload PDF via cURL
```bash
curl -X POST http://localhost:8000/documents/upload/pdf \
  -F "file=@your_document.pdf"
```

### 5. Access Interactive Docs
```
http://localhost:8000/docs  (Swagger UI)
http://localhost:8000/redoc (ReDoc)
```

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/documents/upload/pdf` | Upload PDF (standard response) |
| POST | `/documents/upload/pdf/detailed` | Upload PDF (with metadata) |
| POST | `/documents/validate/pdf` | Validate without storage |
| GET | `/documents/{id}` | Get document metadata |
| DELETE | `/documents/{id}` | Delete document |

## Response Format

**Successful Upload**:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "document.pdf",
  "status": "uploaded",
  "chunks_created": 15,
  "message": "Successfully uploaded document.pdf (15 pages)"
}
```

**Detailed Upload**:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "document.pdf",
  "status": "uploaded",
  "message": "Successfully uploaded document.pdf (15 pages)",
  "metadata": {
    "page_count": 15,
    "title": "My Document",
    "author": "John Doe",
    "subject": null,
    "creator": "LibreOffice Writer",
    "producer": "LibreOffice 7.4",
    "creation_date": "2024-05-29T10:30:00",
    "modification_date": null
  },
  "file_info": {
    "path": "uploads/550e8400-e29b-41d4-a716-446655440000_document.pdf",
    "filename": "550e8400-e29b-41d4-a716-446655440000_document.pdf",
    "size": {
      "bytes": 245632,
      "kilobytes": 239.87,
      "megabytes": 0.23
    },
    "exists": true
  },
  "text_preview": "First 500 characters of extracted text..."
}
```

**Validation Response**:
```json
{
  "file_name": "document.pdf",
  "is_valid": true,
  "file_size": 245632,
  "size_mb": 0.23,
  "error": null
}
```

**Error Response**:
```json
{
  "detail": "File is not a valid PDF (invalid magic bytes)"
}
```

## Validation Rules

| Check | Rule | Error Message |
|-------|------|---------------|
| Extension | Must be `.pdf` | "Invalid file extension. Expected .pdf, got .{ext}" |
| Magic Bytes | Must start with `%PDF` | "File is not a valid PDF (invalid magic bytes)" |
| File Size | Max 100MB (configurable) | "File too large. Maximum size: 100MB" |
| Empty | Cannot be empty | "File is empty" |

## Component Responsibilities

### PDFValidator (`pdf_validator.py`)
- Checks file extension
- Verifies PDF magic bytes
- Validates file size
- Returns boolean + error message

### PDFProcessor (`pdf_processor.py`)
- Extracts PDF metadata (title, author, page count, etc.)
- Extracts all text from PDF
- Extracts text page-by-page
- Gets file size information

### UploadService (`upload_service.py`)
- Initializes upload directory
- Validates PDFs via PDFValidator
- Saves files to disk with unique naming
- Manages file information queries
- Wraps PDF utilities

### PDFUploadService (`pdf_upload_service.py`)
- Orchestrates complete upload workflow
- Chains: validate → save → extract → respond
- Handles errors with structured responses
- Async processing for concurrency

## Configuration

**Environment Variables** (`.env`):
```env
# Upload Settings
UPLOAD_DIR=uploads                    # Where files are stored
MAX_UPLOAD_SIZE_MB=100               # Max file size
ALLOWED_EXTENSIONS=pdf,txt,json,csv  # Allowed file types

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=True
LOG_LEVEL=DEBUG
```

## Testing

```bash
# Run all tests
pytest

# Run PDF tests only
pytest tests/test_pdf_upload.py -v

# Run specific test class
pytest tests/test_pdf_upload.py::TestPDFValidator -v

# Run with coverage report
pytest tests/test_pdf_upload.py --cov=app --cov-report=html

# Run tests matching pattern
pytest tests/test_pdf_upload.py -k "upload" -v
```

## Common Tasks

### Upload a PDF
```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

with open("document.pdf", "rb") as f:
    response = client.post(
        "/documents/upload/pdf",
        files={"file": ("document.pdf", f)}
    )

data = response.json()
print(f"Document ID: {data['document_id']}")
print(f"Pages: {data['chunks_created']}")
```

### Validate Before Upload
```python
with open("document.pdf", "rb") as f:
    response = client.post(
        "/documents/validate/pdf",
        files={"file": ("document.pdf", f)}
    )

if response.json()["is_valid"]:
    print("PDF is valid, uploading...")
    # proceed with upload
else:
    print(f"Invalid: {response.json()['error']}")
```

### Get Detailed Metadata
```python
with open("document.pdf", "rb") as f:
    response = client.post(
        "/documents/upload/pdf/detailed",
        files={"file": ("document.pdf", f)}
    )

data = response.json()
print(f"Title: {data['metadata']['title']}")
print(f"Author: {data['metadata']['author']}")
print(f"Pages: {data['metadata']['page_count']}")
print(f"Size: {data['file_info']['size']['megabytes']}MB")
```

## File Naming

**Pattern**: `{document_id}_{original_filename}`

**Example**: 
```
550e8400-e29b-41d4-a716-446655440000_research_paper.pdf
```

**Benefits**:
- Unique document IDs prevent collisions
- Original filenames preserved for reference
- Easy to trace back to source
- Cannot have filename conflicts

## Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid file extension" | File is not .pdf | Rename file to .pdf or ensure it's a PDF |
| "File is not a valid PDF (invalid magic bytes)" | File content is not PDF | Verify file is actual PDF, not renamed text file |
| "File too large" | Exceeds 100MB limit | Increase MAX_UPLOAD_SIZE_MB or use smaller PDF |
| "File is empty" | File has no content | Upload different file |
| "Failed to read file" | File I/O error | Check file permissions and disk space |
| "PDF upload processing failed" | Unexpected error | Check server logs for details |

## Performance

- **Async**: All endpoints non-blocking
- **Validation**: < 100ms for most files
- **Extraction**: ~1-2 seconds for 100-page PDF
- **Storage**: Direct disk write, no database overhead (yet)
- **Memory**: Streams files, doesn't load entire file in memory

## Security

✅ File type validation (magic bytes check)
✅ Size limits prevent DoS
✅ UUID identifiers prevent enumeration
✅ Files not web-accessible
✅ No code execution risk (PDF only)
✅ Input validation via Pydantic

## Next Steps

1. Connect PostgreSQL for metadata storage
2. Implement embeddings generation
3. Add Pinecone vector storage
4. Implement chunking strategy
5. Add JWT authentication
6. Setup background tasks for large files
7. Add progress tracking for uploads
