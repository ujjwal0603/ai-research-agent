# PDF Text Extraction Flow Documentation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Application Layer                             │
│  Routes / APIs (extract_full_text, extract_pages, etc.)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              PDFExtractionService (High-level)                  │
│  - Unified interface                                             │
│  - Error handling                                                │
│  - Caching                                                       │
│  - Format conversion                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              PDFExtractor (Core engine)                         │
│  - PyMuPDF (fitz) wrapper                                        │
│  - Page iteration                                                │
│  - Metadata extraction                                           │
│  - Coordinate-based extraction                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   PyMuPDF (fitz)                                │
│  - PDF parsing                                                   │
│  - Text extraction                                               │
│  - Metadata reading                                              │
│  - Layout analysis                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Complete Text Extraction

```
1. CLIENT REQUEST
   └─→ POST /extract?file_path=document.pdf

2. ROUTE HANDLER
   ├─→ Validates file_path
   ├─→ Calls: extraction_service.extract_full_text()
   └─→ Returns JSON response

3. PDFExtractionService.extract_full_text()
   ├─→ Checks cache (if enabled)
   │   └─→ Return cached result
   ├─→ Log: "Extracting full text from: {file_path}"
   └─→ Calls: extractor.extract_text(file_path)

4. PDFExtractor.extract_text()
   ├─→ Check file exists
   ├─→ Time extraction start
   ├─→ fitz.open(file_path)
   │   └─→ Open PDF for reading
   │
   ├─→ FOR each page (0 to page_count-1):
   │   ├─→ Call: _extract_page_text(pdf, page_num)
   │   │   ├─→ Get page object
   │   │   ├─→ page.get_text("text" or "raw")
   │   │   │   └─→ Extract text with layout preservation
   │   │   ├─→ page.get_text("blocks")
   │   │   │   └─→ Get raw text blocks
   │   │   ├─→ Count characters & lines
   │   │   └─→ Return PageContent(page_num, text, blocks, char_count, line_count)
   │   ├─→ Append to pages_content list
   │   └─→ On error: log warning, increment failed_pages count
   │
   ├─→ pdf_document.close()
   ├─→ _combine_pages(pages_content)
   │   └─→ Join with page separators: "="*80
   └─→ Calculate ExtractionMetadata:
       ├─→ total_pages: len(pdf_document)
       ├─→ total_chars: sum(page.char_count for each page)
       ├─→ total_lines: sum(page.line_count for each page)
       ├─→ extraction_time: elapsed time
       ├─→ success_pages: successful extractions
       ├─→ failed_pages: failed extractions
       └─→ errors: list of error messages

5. RESPONSE AGGREGATION
   ├─→ Check extraction time vs max_extraction_time
   ├─→ Cache result (if use_cache=True)
   └─→ Return:
       {
           "success": True,
           "text": "Full extracted text...",
           "metadata": {
               "total_pages": 10,
               "total_chars": 50000,
               "total_lines": 2500,
               "extraction_time": 2.34,
               "success_pages": 10,
               "failed_pages": 0,
               "errors": []
           },
           "error": None
       }

6. CLIENT RECEIVES RESPONSE
   └─→ Full text ready for embedding/processing
```

## Data Flow: Page-by-Page Extraction

```
1. extract_pages(file_path, page_range=(1, 5))
   │
   ├─→ Call: extractor.extract_text_by_page(file_path)
   │   └─→ Returns: (pages: List[PageContent], metadata)
   │
   ├─→ Apply page range filter
   │   └─→ Filter pages to only 1-5
   │
   └─→ Format page data
       └─→ [
           {
               "page": 1,
               "text": "Page 1 content...",
               "char_count": 5000,
               "line_count": 250
           },
           ...
       ]
```

## Data Flow: Layout-Aware Extraction

```
1. extract_with_layout(file_path)
   │
   ├─→ Call: extractor.extract_with_coordinates(file_path)
   │   │
   │   ├─→ FOR each page:
   │   │   ├─→ page.get_text("blocks")
   │   │   │   └─→ Returns: [x0, y0, x1, y1, text, block_num, block_type]
   │   │   │       (bbox coordinates and text)
   │   │   │
   │   │   ├─→ FOR each block (if text block):
   │   │   │   └─→ Append:
   │   │   │       {
   │   │   │           "page": 1,
   │   │   │           "bbox": (x0, y0, x1, y1),
   │   │   │           "text": "Block text",
   │   │   │           "block_type": "text"
   │   │   │       }
   │   │   └─→ On error: log, continue
   │   │
   │   └─→ Return all_blocks
   │
   └─→ Use cases:
       - Table detection (rows based on y-coordinates)
       - Column detection (columns based on x-coordinates)
       - Reading order (sort by y, then x)
       - Layout-aware chunking
```

## Component Responsibilities

### PDFExtractor (Low-level engine)

**Methods**:
- `extract_text(file_path)` → (str, ExtractionMetadata)
  - Opens PDF with PyMuPDF
  - Iterates all pages
  - Extracts text with layout preservation
  - Combines pages with separators
  - Returns full text + metadata

- `extract_text_by_page(file_path)` → (List[PageContent], ExtractionMetadata)
  - Same as above but returns individual page objects
  - Useful for random access to specific pages

- `extract_with_coordinates(file_path)` → (List[Dict], ExtractionMetadata)
  - Gets block-level text with bounding boxes
  - Useful for layout analysis

- `extract_metadata(file_path)` → Dict
  - Reads PDF metadata (title, author, etc.)
  - Counts pages
  - Gets file size

**Error Handling**:
```python
try:
    pdf_document = fitz.open(file_path)
    for page_num in range(len(pdf_document)):
        try:
            page_content = _extract_page_text(...)
        except Exception as e:
            # Log warning, increment failed_pages
            errors.append(f"Page {page_num + 1}: {error}")
    pdf_document.close()
except Exception as e:
    # Fatal error (can't open file)
    raise RuntimeError(...)
```

### PDFExtractionService (High-level API)

**Methods**:
- `extract_full_text(file_path, use_cache=False)` → Dict
  - Wraps PDFExtractor.extract_text()
  - Adds caching
  - Provides error handling
  - Returns structured response

- `extract_pages(file_path, page_range=None)` → Dict
  - Wraps PDFExtractor.extract_text_by_page()
  - Filters page range
  - Returns page-organized data

- `extract_with_layout(file_path)` → Dict
  - Wraps PDFExtractor.extract_with_coordinates()
  - Returns spatial coordinate data

- `extract_metadata(file_path)` → Dict
  - Wraps PDFExtractor.extract_metadata()

- `extract_text_snippet(file_path, page, max_chars=500)` → str
  - Quick extraction from single page
  - Useful for previews

**Features**:
- Caching for repeated documents
- Structured error responses (never throws)
- Logging at each step
- Time tracking
- Cache statistics

## Error Handling Strategy

```
┌─────────────────────────────────────┐
│    Extraction Request               │
└────────────┬────────────────────────┘
             │
     ┌───────▼────────┐
     │ File exists?   │
     └───────┬────────┘
             │
      ┌──────┴──────┐
      │NO           │YES
      ↓             ↓
  FileNotFound   ┌──────────────────┐
  Error          │ Open with PyMuPDF│
                 └──────┬───────────┘
                        │
                   ┌────▼─────┐
                   │ Valid PDF?│
                   └────┬─────┘
                        │
                   ┌────┴────┐
                   │NO       │YES
                   ↓         ↓
              RuntimeError  ┌─────────────────────┐
                            │ Iterate pages       │
                            └──────┬──────────────┘
                                   │
                          ┌────────▼─────────┐
                          │ Extract page N   │
                          └────────┬─────────┘
                                   │
                            ┌──────┴──────┐
                            │No error│Error
                            ↓        ↓
                        Add page  Log warning
                        to list   Increment
                                  failed count
                                   │
                            ┌──────▼─────┐
                            │More pages? │
                            └──────┬─────┘
                                   │
                            ┌──────┴──────┐
                            │YES         │NO
                            ↓            ↓
                     Continue loop  Combine pages
                                    Create response
                                    Return
```

## Data Structures

### PageContent
```python
@dataclass
class PageContent:
    page_number: int              # 1-indexed
    text: str                     # Extracted text
    blocks: List[Dict]            # Raw PyMuPDF blocks
    char_count: int               # Number of characters
    line_count: int               # Number of lines
```

### ExtractionMetadata
```python
@dataclass
class ExtractionMetadata:
    total_pages: int              # Total pages in PDF
    total_chars: int              # Total characters extracted
    total_lines: int              # Total lines extracted
    extraction_time: float        # Elapsed time in seconds
    success_pages: int            # Pages extracted successfully
    failed_pages: int             # Pages that failed
    errors: List[str]             # List of error messages
```

### Service Response (Full Text)
```python
{
    "success": bool,
    "text": str or None,          # Full extracted text
    "metadata": {
        "total_pages": int,
        "total_chars": int,
        "total_lines": int,
        "extraction_time": float,
        "success_pages": int,
        "failed_pages": int,
        "errors": List[str]
    },
    "error": str or None          # Error message if failed
}
```

### Service Response (Pages)
```python
{
    "success": bool,
    "pages": [
        {
            "page": int,
            "text": str,
            "char_count": int,
            "line_count": int
        }
    ],
    "metadata": { ... },
    "error": str or None
}
```

## Performance Characteristics

**Extraction Speed** (per 100-page PDF):
- Validation: 1-5ms
- PDF open: 10-50ms
- Per-page extraction: 10-50ms
- Total: 1-5 seconds

**Memory Usage**:
- File buffer: 1-100MB
- PyMuPDF parser: 5-20MB
- Extracted text: Same as file size
- Total peak: ~1.5x file size

**Optimization Tips**:
1. Use `extract_pages()` if you only need specific pages
2. Enable caching for repeated documents
3. Use `extract_text_snippet()` for previews
4. Use `extract_with_layout()` only when layout is needed
5. Implement background tasks for large PDFs

## Comparison: PDFExtractor vs PyPDF2

| Feature | PDFExtractor (PyMuPDF) | PyPDF2 |
|---------|------------------------|--------|
| Text Quality | ⭐⭐⭐⭐⭐ Better | ⭐⭐⭐ Good |
| Layout Preservation | ⭐⭐⭐⭐⭐ Yes | ⭐⭐ Limited |
| Speed | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐ Okay |
| Coordinates | ⭐⭐⭐⭐⭐ Built-in | ⭐⭐ Requires extra work |
| Metadata | ⭐⭐⭐⭐⭐ Complete | ⭐⭐⭐ Basic |
| Encryption Support | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Good |
| Memory Usage | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Lower |
| License | AGPL/Commercial | BSD | 

## Usage Examples

### Basic Extraction
```python
service = PDFExtractionService()

# Extract full text
result = service.extract_full_text("document.pdf")
if result["success"]:
    text = result["text"]
    metadata = result["metadata"]
    print(f"Extracted {metadata['total_chars']} characters")
```

### Page-by-Page
```python
# Extract specific pages
result = service.extract_pages("document.pdf", page_range=(1, 5))
for page in result["pages"]:
    print(f"Page {page['page']}: {page['char_count']} chars")
```

### Layout Analysis
```python
# Extract with coordinates
result = service.extract_with_layout("document.pdf")
for block in result["blocks"]:
    print(f"Block at {block['bbox']}: {block['text']}")
```

### Caching
```python
# First call - extracts and caches
result1 = service.extract_full_text("document.pdf", use_cache=True)

# Second call - uses cache (instant)
result2 = service.extract_full_text("document.pdf", use_cache=True)

stats = service.get_cache_stats()
print(f"Cached files: {stats['cached_files']}")
```

## Next Steps

1. **Integrate with Embeddings**: Text → chunks → embeddings
2. **Add Chunking Strategy**: Smart chunking based on layout
3. **Add Table Detection**: Identify and extract tables
4. **Add OCR Support**: For scanned PDFs (Tesseract)
5. **Add Compression**: Store extracted text efficiently
6. **Add Async Operations**: Background extraction for large PDFs
7. **Add Progress Tracking**: Track extraction progress
8. **Add Quality Metrics**: Measure extraction quality
