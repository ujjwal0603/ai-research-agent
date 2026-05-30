# PDF Upload Architecture & Data Flow

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CLIENT (Browser/cURL/SDK)                       │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTP POST /documents/upload/pdf
                          │ multipart/form-data: file
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Route Handler                             │
│  app/api/routes/upload.py::upload_pdf()                             │
│  ✓ Validates file is provided                                       │
│  ✓ Reads file content as bytes                                      │
│  ✓ Calls PDFUploadService.process_pdf_upload()                      │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│              PDFUploadService (Orchestrator)                         │
│  app/services/pdf_upload_service.py                                 │
│                                                                       │
│  Step 1: Validate PDF                                               │
│  ├─→ calls: PDFValidator.validate()                                 │
│  ├─→ checks: extension, magic bytes, size                           │
│  └─→ on fail: returns (False, error_dict)                           │
│                                                                       │
│  Step 2: Save File                                                  │
│  ├─→ calls: UploadService.save_file()                               │
│  ├─→ generates UUID for document_id                                 │
│  ├─→ names file: {uuid}_{filename}                                  │
│  └─→ writes to disk                                                 │
│                                                                       │
│  Step 3: Extract Metadata                                           │
│  ├─→ calls: PDFProcessor.extract_metadata()                         │
│  ├─→ reads PDF properties via PyPDF2                                │
│  └─→ returns: {page_count, title, author, ...}                      │
│                                                                       │
│  Step 4: Extract Text                                               │
│  ├─→ calls: PDFProcessor.extract_text()                             │
│  ├─→ reads each page                                                │
│  ├─→ combines text with page separators                             │
│  └─→ returns: full_text                                             │
│                                                                       │
│  Step 5: Get File Info                                              │
│  ├─→ calls: UploadService.get_file_info()                           │
│  ├─→ gets file size, path, existence                                │
│  └─→ returns: {path, size_bytes, size_kb, size_mb}                  │
│                                                                       │
│  Aggregates all data into response_dict                             │
│  Returns: (True, response_dict)                                     │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│            PDFValidator (Validation Layer)                           │
│  app/utils/pdf_validator.py                                         │
│                                                                       │
│  validate_extension(filename)                                       │
│  ├─→ Checks: filename.lower().endswith('.pdf')                      │
│  └─→ Returns: bool                                                  │
│                                                                       │
│  validate_mime_type(file_content)                                   │
│  ├─→ Checks: content.startswith(b'%PDF')                            │
│  └─→ Returns: bool  (magic bytes verification)                      │
│                                                                       │
│  validate_size(file_size, max_mb)                                   │
│  ├─→ Checks: file_size <= max_mb * 1024 * 1024                      │
│  └─→ Returns: bool                                                  │
│                                                                       │
│  validate(filename, file_content, max_mb)                           │
│  ├─→ Calls all above validators                                     │
│  └─→ Returns: (is_valid: bool, error_msg: str|None)                 │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│           PDFProcessor (Extraction Layer)                            │
│  app/utils/pdf_processor.py                                         │
│                                                                       │
│  extract_metadata(file_path) → Dict                                 │
│  ├─→ Opens PDF with PyPDF2.PdfReader                                │
│  ├─→ Reads: /Title, /Author, /Subject, /Creator, /Producer         │
│  ├─→ Counts pages                                                   │
│  └─→ Returns: {page_count, title, author, subject, creator, ...}    │
│                                                                       │
│  extract_text(file_path) → str                                      │
│  ├─→ Iterates through all pages                                     │
│  ├─→ Calls: page.extract_text() for each                            │
│  ├─→ Adds page separators: "--- Page N ---"                         │
│  └─→ Returns: combined_text                                         │
│                                                                       │
│  extract_text_by_page(file_path) → List[str]                        │
│  ├─→ Returns list of strings, one per page                          │
│  └─→ Empty string if extraction fails for page                      │
│                                                                       │
│  get_file_size_info(file_path) → Dict                               │
│  ├─→ Gets: Path.stat().st_size                                      │
│  └─→ Returns: {bytes, kilobytes, megabytes}                         │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│           UploadService (Business Logic Layer)                       │
│  app/services/upload_service.py                                     │
│                                                                       │
│  __init__(upload_dir, allowed_extensions, max_size_mb)              │
│  ├─→ Creates upload directory if missing                            │
│  └─→ Stores config as instance variables                            │
│                                                                       │
│  validate_pdf(filename, file_content) → (bool, str|None)            │
│  ├─→ Delegates to: PDFValidator.validate()                          │
│  └─→ Logs warnings on failure                                       │
│                                                                       │
│  save_file(document_id, filename, content) → str                    │
│  ├─→ Creates path: {upload_dir}/{document_id}_{filename}            │
│  ├─→ Calls: Path.write_bytes(content)                               │
│  └─→ Returns: file_path (str)                                       │
│                                                                       │
│  extract_pdf_metadata(file_path) → Dict                             │
│  ├─→ Delegates to: PDFProcessor.extract_metadata()                  │
│  └─→ Logs errors with file path                                     │
│                                                                       │
│  extract_pdf_text(file_path) → str                                  │
│  ├─→ Delegates to: PDFProcessor.extract_text()                      │
│  └─→ Returns extracted text                                         │
│                                                                       │
│  get_file_info(file_path) → Dict                                    │
│  ├─→ Gets size via: PDFProcessor.get_file_size_info()               │
│  └─→ Returns: {path, filename, size, exists}                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Dependency Injection Graph

```
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI Route Handler                          │
│                   (upload_pdf endpoint)                           │
└─────────┬──────────────────────────────────────────────────────┬─┘
          │                                                        │
          │ Depends(get_pdf_upload_service)                       │
          │                                                        │
          ↓                                                        ↓
    ┌─────────────────────────────────┐      ┌──────────────────────────────┐
    │  PDFUploadService               │      │  UploadFile (FastAPI)         │
    │  (orchestrates workflow)         │      │  (file from request)          │
    └─────────┬───────────────────────┘      └──────────────────────────────┘
              │ Depends(get_upload_service)
              │
              ↓
         ┌──────────────────────┐
         │  UploadService       │
         │  (file operations)   │
         └──────┬───────────────┘
                │
                ├─→ PDFValidator (validation)
                ├─→ PDFProcessor (extraction)
                └─→ Logger (logging)
```

## Class Structure

```
PDFValidator (Static utility class)
├── validate_extension(filename: str) → bool
├── validate_mime_type(file_content: bytes) → bool
├── validate_size(file_size: int, max_mb: int) → bool
└── validate(filename, content, max_mb) → (bool, str|None)

PDFProcessor (Static utility class)
├── extract_metadata(file_path: str) → Dict
├── extract_text(file_path: str) → str
├── extract_text_by_page(file_path: str) → List[str]
└── get_file_size_info(file_path: str) → Dict

UploadService (Instance class)
├── __init__(upload_dir, allowed_extensions, max_size_mb)
├── validate_pdf(filename, content) → (bool, str|None)
├── save_file(document_id, filename, content) → str
├── extract_pdf_metadata(file_path) → Dict
├── extract_pdf_text(file_path) → str
├── get_file_info(file_path) → Dict
└── create_upload_response(...) → UploadResponse

PDFUploadService (Async orchestrator)
├── __init__(upload_service: UploadService)
├── process_pdf_upload(filename, content) → (bool, Dict)
└── validate_pdf_only(filename, content) → (bool, str|None)
```

## Error Handling Flow

```
                      PDF Upload Request
                              │
                              ↓
                    ┌─────────────────────┐
                    │ Validate PDF        │
                    └─────────┬───────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
          [INVALID]                    [VALID]
                │                           │
                ↓                           ↓
        ┌─────────────────┐      ┌──────────────────┐
        │ Return Error    │      │ Save File        │
        │ - Extension     │      └────────┬─────────┘
        │ - Magic Bytes   │               │
        │ - File Size     │               ↓
        │ - Empty File    │      ┌──────────────────┐
        └─────────────────┘      │ Extract Metadata │
                                 └────────┬─────────┘
                                          │
                         ┌────────────────┴────────────────┐
                         │                                 │
                  [SUCCESS]                          [ERROR]
                         │                                 │
                         ↓                                 ↓
                ┌──────────────────┐         ┌─────────────────────┐
                │ Extract Text     │         │ Return Error Dict   │
                └────────┬─────────┘         │ - Log Exception     │
                         │                   │ - status: failed    │
                         ↓                   └─────────────────────┘
                ┌──────────────────┐
                │ Get File Info    │
                └────────┬─────────┘
                         │
                         ↓
                ┌──────────────────┐
                │ Return Success   │
                │ - document_id    │
                │ - metadata       │
                │ - text_preview   │
                │ - file_info      │
                └──────────────────┘
```

## State Transitions

```
User selects file
        ↓
    [PENDING]
        ├─ await file.read()
        │
        ↓
    [VALIDATING]
        ├─ PDFValidator.validate()
        ├─ Check extension
        ├─ Check magic bytes
        ├─ Check file size
        │
        ├─→ INVALID: return (False, error)
        │
        ├─→ VALID:
        │
        ↓
    [SAVING]
        ├─ Generate UUID
        ├─ Create filename
        ├─ Write to disk
        │
        ├─→ FAILED: return error
        │
        ├─→ SUCCESS:
        │
        ↓
    [EXTRACTING]
        ├─ Extract metadata
        ├─ Extract text
        ├─ Get file info
        │
        ├─→ PARTIAL_ERROR: continue with available data
        │
        ↓
    [COMPLETE]
        └─ Return success response
```

## Memory & Performance Profile

**Input**:
- File size: 1-100 MB (configurable)
- Pages: 1-5000+ 
- Text per page: 1-100KB

**Processing Times** (estimated):
- Validation: 1-10ms
- File save: 10-500ms (depends on disk I/O)
- Metadata extraction: 5-50ms
- Text extraction: 100ms - 5s (scales with page count)
- Total: 200ms - 6s for typical 100-page PDF

**Memory Usage** (per request):
- File buffer: 1-100MB in RAM
- PDF reader: ~5-20MB
- Extracted text: Same as file size
- Response dict: <10MB
- **Peak**: ~1.5x file size

**Optimization Tips**:
- Implement background tasks for large files
- Add request timeout
- Stream responses if needed
- Implement caching for repeated documents
