# PDF Upload Implementation Guide

## Overview

The PDF upload functionality provides production-ready file handling with:
- ✅ Comprehensive PDF validation (extension, magic bytes, size)
- ✅ Async upload endpoint with structured responses
- ✅ Metadata extraction (page count, author, title, etc.)
- ✅ Text content extraction for embeddings
- ✅ Error handling with detailed feedback
- ✅ Secure file storage with unique identifiers
- ✅ Full test coverage

## Architecture

```
Upload Request
    ↓
PDFUploadService.process_pdf_upload()
    ├─ PDFValidator.validate() ──→ Check extension/magic bytes/size
    ├─ UploadService.save_file() ──→ Store to disk
    ├─ PDFProcessor.extract_metadata() ──→ Get PDF properties
    ├─ PDFProcessor.extract_text() ──→ Get page content
    └─ UploadService.get_file_info() ──→ File statistics
    ↓
Structured Response
```

## Components

### 1. **PDFValidator** (`app/utils/pdf_validator.py`)

**Purpose**: Validate PDF files before processing

**Methods**:
- `validate_extension(filename)` - Checks .pdf extension
- `validate_mime_type(file_content)` - Verifies PDF magic bytes (%PDF)
- `validate_size(file_size, max_size_mb)` - Ensures file within limits
- `validate(filename, file_content, max_size_mb)` - Complete validation

**Example**:
```python
is_valid, error = PDFValidator.validate("document.pdf", pdf_bytes, max_size_mb=100)
if not is_valid:
    print(f"Validation failed: {error}")
```

**Validation Checks**:
- ✅ File must have `.pdf` extension
- ✅ File must start with PDF magic bytes (`%PDF`)
- ✅ File size must not exceed configured limit (default 100MB)

### 2. **PDFProcessor** (`app/utils/pdf_processor.py`)

**Purpose**: Extract text and metadata from PDF files

**Methods**:
- `extract_metadata(file_path)` - Gets PDF properties
  - Page count, title, author, subject, creation date, etc.
- `extract_text(file_path)` - Extracts all text from all pages
  - Includes page separators
  - Handles extraction errors gracefully
- `extract_text_by_page(file_path)` - Returns text per page
  - List where each item is a page's text
  - Empty string if extraction fails
- `get_file_size_info(file_path)` - File size in multiple units
  - Returns bytes, kilobytes, megabytes

**Example**:
```python
# Extract metadata
metadata = PDFProcessor.extract_metadata("document.pdf")
print(f"Pages: {metadata['page_count']}, Author: {metadata['author']}")

# Extract all text
text = PDFProcessor.extract_text("document.pdf")
print(f"Extracted {len(text)} characters")

# Extract by page
pages = PDFProcessor.extract_text_by_page("document.pdf")
print(f"Document has {len(pages)} pages")
```

### 3. **UploadService** (`app/services/upload_service.py`)

**Purpose**: Handle file storage and high-level operations

**Key Methods**:
- `__init__(upload_dir, allowed_extensions, max_size_mb)` - Initialize service
  - Creates upload directory if missing
  - Sets size limits and allowed extensions
- `validate_pdf(filename, file_content)` - Wrapper around PDFValidator
- `save_file(document_id, filename, content)` - Write file to disk
  - Stores as: `{upload_dir}/{document_id}_{filename}`
  - Unique naming prevents collisions
- `extract_pdf_metadata(file_path)` - Wrapper around PDFProcessor
- `extract_pdf_text(file_path)` - Wrapper around PDFProcessor
- `get_file_info(file_path)` - File statistics and location

**Example**:
```python
service = UploadService(
    upload_dir="uploads",
    allowed_extensions="pdf",
    max_size_mb=100
)

is_valid, error = service.validate_pdf("doc.pdf", file_bytes)
if is_valid:
    path = service.save_file("uuid-123", "doc.pdf", file_bytes)
    metadata = service.extract_pdf_metadata(path)
```

### 4. **PDFUploadService** (`app/services/pdf_upload_service.py`)

**Purpose**: Orchestrate complete PDF upload workflow

**Methods**:
- `process_pdf_upload(filename, file_content)` - Full upload workflow
  - Returns: `(success: bool, response_dict: Dict)`
  - Calls: validate → save → extract metadata → extract text → get info
  - Logs each step for debugging
- `validate_pdf_only(filename, file_content)` - Quick validation without storage

**Workflow**:
```python
success, data = await pdf_upload_service.process_pdf_upload("doc.pdf", bytes)

if success:
    document_id = data["document_id"]
    metadata = data["metadata"]  # Page count, author, etc.
    text = data["text_preview"]  # First 500 chars
    file_path = data["file_path"]  # Disk location
else:
    error = data["error"]
```

**Response Structure on Success**:
```python
{
    "document_id": "uuid-string",
    "file_name": "document.pdf",
    "status": "uploaded",
    "file_path": "uploads/uuid_document.pdf",
    "metadata": {
        "page_count": 10,
        "title": "My Document",
        "author": "John Doe",
        "subject": None,
        "creator": "LibreOffice",
        "production": "GNU Ghostscript",
        "creation_date": "2024-05-29T...",
        "modification_date": None
    },
    "text_preview": "First 500 characters...",
    "file_info": {
        "path": "uploads/uuid_document.pdf",
        "filename": "uuid_document.pdf",
        "size": {
            "bytes": 245632,
            "kilobytes": 239.87,
            "megabytes": 0.23
        },
        "exists": true
    },
    "message": "Successfully uploaded document.pdf (10 pages)"
}
```

## API Endpoints

### Upload PDF (Standard Response)
```
POST /documents/upload/pdf
Content-Type: multipart/form-data

Response:
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "document.pdf",
    "status": "uploaded",
    "chunks_created": 10,
    "message": "Successfully uploaded document.pdf (10 pages)"
}
```

### Upload PDF (Detailed Response)
```
POST /documents/upload/pdf/detailed
Content-Type: multipart/form-data

Response:
{
    "document_id": "...",
    "file_name": "document.pdf",
    "status": "uploaded",
    "message": "...",
    "metadata": { /* PDF properties */ },
    "file_info": { /* Size and path */ },
    "text_preview": "First 500 characters..."
}
```

### Validate PDF (Without Storage)
```
POST /documents/validate/pdf
Content-Type: multipart/form-data

Response:
{
    "file_name": "document.pdf",
    "is_valid": true,
    "file_size": 245632,
    "size_mb": 0.23,
    "error": null
}
```

## File Storage

**Location**: Configured via `UPLOAD_DIR` in `.env` (default: `uploads/`)

**File Naming Convention**: `{document_id}_{original_filename}`
- Example: `550e8400-e29b-41d4-a716-446655440000_my_document.pdf`
- Prevents filename collisions
- UUID ensures uniqueness

**Directory Structure**:
```
uploads/
├── 550e8400-e29b-41d4-a716-446655440000_document1.pdf
├── 660e8400-e29b-41d4-a716-446655440001_document2.pdf
└── 770e8400-e29b-41d4-a716-446655440002_document3.pdf
```

## Configuration

**Environment Variables** (in `.env`):
```env
# Upload constraints
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=100
ALLOWED_EXTENSIONS=pdf,txt,json,csv

# PDF extraction
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

## Error Handling

**Validation Errors**:
- Invalid extension → "Invalid file extension. Expected .pdf, got .txt"
- Not a PDF → "File is not a valid PDF (invalid magic bytes)"
- Too large → "File too large. Maximum size: 100MB"
- Empty file → "File is empty"

**Processing Errors**:
- All exceptions caught and logged with traceback
- User receives meaningful error message
- Technical details logged server-side for debugging

**HTTP Status Codes**:
- `200` - Success
- `400` - Validation error or bad request
- `500` - Server error (unexpected exception)

## Testing

**Test File**: `tests/test_pdf_upload.py`

**Test Coverage**:
- ✅ Validator: extension, magic bytes, size, complete validation
- ✅ Processor: metadata extraction, file size info, text extraction
- ✅ Endpoints: upload success, detailed response, validation-only
- ✅ Error cases: invalid format, missing file, wrong extension

**Run Tests**:
```bash
# All tests
pytest

# Just PDF tests
pytest tests/test_pdf_upload.py -v

# Specific test
pytest tests/test_pdf_upload.py::TestPDFValidator::test_validate_pdf_extension -v

# With coverage
pytest tests/test_pdf_upload.py --cov=app/utils --cov=app/services
```

**Example Test Output**:
```
tests/test_pdf_upload.py::TestPDFValidator::test_validate_pdf_extension PASSED
tests/test_pdf_upload.py::TestPDFValidator::test_validate_pdf_mime_type PASSED
tests/test_pdf_upload.py::TestPDFUploadEndpoint::test_upload_pdf_success PASSED
tests/test_pdf_upload.py::TestPDFUploadEndpoint::test_upload_pdf_detailed PASSED
tests/test_pdf_upload.py::TestPDFUploadEndpoint::test_upload_pdf_invalid_format PASSED
```

## Usage Example

**Python Client**:
```python
import httpx

client = httpx.Client()

# Upload PDF
with open("document.pdf", "rb") as f:
    files = {"file": ("document.pdf", f, "application/pdf")}
    response = client.post("http://localhost:8000/documents/upload/pdf", files=files)

print(response.json())
# {
#     "document_id": "550e8400-...",
#     "file_name": "document.pdf",
#     "status": "uploaded",
#     "chunks_created": 15,
#     "message": "Successfully uploaded document.pdf (15 pages)"
# }

# Validate before upload
with open("document.pdf", "rb") as f:
    files = {"file": ("document.pdf", f, "application/pdf")}
    response = client.post("http://localhost:8000/documents/validate/pdf", files=files)

print(response.json())
# {
#     "file_name": "document.pdf",
#     "is_valid": true,
#     "file_size": 245632,
#     "size_mb": 0.23,
#     "error": null
# }
```

**cURL**:
```bash
# Upload PDF
curl -X POST http://localhost:8000/documents/upload/pdf \
  -F "file=@document.pdf"

# Validate PDF
curl -X POST http://localhost:8000/documents/validate/pdf \
  -F "file=@document.pdf"

# Get detailed info
curl -X POST http://localhost:8000/documents/upload/pdf/detailed \
  -F "file=@document.pdf"
```

## Performance Considerations

- **Async Processing**: All endpoints async for high concurrency
- **Streaming**: File read streams to avoid memory overload
- **Batch Operations**: PDFProcessor supports page-by-page extraction
- **Caching**: Extracted metadata cached in response (not stored in DB yet)
- **Logging**: Structured logs with document IDs for tracing

## Security Notes

- ✅ File validation prevents non-PDF uploads
- ✅ Size limits prevent DoS via large files
- ✅ Files stored outside web root (not directly accessible)
- ✅ UUID document IDs prevent enumeration
- ✅ No arbitrary file execution (PDFs only)
- ✅ Input validation via Pydantic

## Next Steps

1. **Connect to Database**: Store document metadata in PostgreSQL
2. **Add Embeddings**: Extract text → generate embeddings → store in Pinecone
3. **Add Authentication**: Protect endpoints with JWT
4. **Add Cleanup**: Implement file deletion & vector store cleanup
5. **Add Chunking**: Implement smart document chunking for embeddings
6. **Add Monitoring**: Track upload metrics, extraction times, errors
