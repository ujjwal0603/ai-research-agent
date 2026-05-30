# PDF Extraction Quick Reference

## Components

```
app/utils/
├── pdf_extractor.py           ← PDFExtractor (PyMuPDF wrapper)
│   ├── PDFExtractor class
│   ├── PageContent dataclass
│   └── ExtractionMetadata dataclass
│
app/services/
├── pdf_extraction_service.py   ← PDFExtractionService (high-level API)
│   └── PDFExtractionService class
```

## Install & Setup

```bash
# Install dependencies
pip install PyMuPDF==1.23.8

# Or update existing installation
pip install -r requirements.txt
```

## Service-Based Architecture

```
┌─────────────────┐
│  API Route      │
│  (endpoint)     │
└────────┬────────┘
         │ calls
         ↓
┌─────────────────────────────────────┐
│ PDFExtractionService                │
│ - extract_full_text()               │
│ - extract_pages()                   │
│ - extract_with_layout()             │
│ - extract_metadata()                │
│ - extract_text_snippet()            │
│ - Caching                           │
│ - Error handling                    │
└────────┬────────────────────────────┘
         │ calls
         ↓
┌─────────────────────────────────────┐
│ PDFExtractor                        │
│ - extract_text()                    │
│ - extract_text_by_page()            │
│ - extract_with_coordinates()        │
│ - extract_metadata()                │
│ - Page iteration                    │
│ - Error recovery                    │
└────────┬────────────────────────────┘
         │ uses
         ↓
┌─────────────────────────────────────┐
│ PyMuPDF (fitz)                      │
│ - PDF parsing                       │
│ - Text extraction                   │
│ - Layout analysis                   │
└─────────────────────────────────────┘
```

## API Overview

### Extract Full Text
```python
service = PDFExtractionService()
result = service.extract_full_text("document.pdf")

# result = {
#     "success": True,
#     "text": "Full PDF text...",
#     "metadata": {
#         "total_pages": 10,
#         "total_chars": 50000,
#         "extraction_time": 2.34,
#         "success_pages": 10,
#         "failed_pages": 0,
#         "errors": []
#     },
#     "error": None
# }
```

### Extract by Pages
```python
result = service.extract_pages("document.pdf", page_range=(1, 5))

# result = {
#     "success": True,
#     "pages": [
#         {"page": 1, "text": "Page 1 text...", "char_count": 5000},
#         {"page": 2, "text": "Page 2 text...", "char_count": 5100},
#         ...
#     ],
#     "metadata": { ... },
#     "error": None
# }
```

### Extract with Layout
```python
result = service.extract_with_layout("document.pdf")

# result = {
#     "success": True,
#     "blocks": [
#         {
#             "page": 1,
#             "bbox": (50, 50, 550, 100),  # (x0, y0, x1, y1)
#             "text": "Block text"
#         },
#         ...
#     ],
#     "metadata": { ... },
#     "error": None
# }
```

### Extract Metadata Only
```python
result = service.extract_metadata("document.pdf")

# result = {
#     "success": True,
#     "metadata": {
#         "title": "Document Title",
#         "author": "Author Name",
#         "subject": "Subject",
#         "page_count": 10,
#         "file_size_bytes": 1024000,
#         "is_encrypted": False,
#         "creation_date": "2024-01-01T00:00:00",
#         ...
#     },
#     "error": None
# }
```

### Extract Text Snippet
```python
snippet = service.extract_text_snippet(
    "document.pdf",
    page=1,
    max_chars=500
)

# snippet = "First 500 characters from page 1..."
```

## Error Handling

**All methods return structured responses** (never throw exceptions):

```python
result = service.extract_full_text("nonexistent.pdf")

if result["success"]:
    print(f"Extracted {result['metadata']['total_chars']} chars")
else:
    print(f"Error: {result['error']}")
    # Error: File not found: nonexistent.pdf
```

**Partial Failures Handled Gracefully**:

```python
# If 2 of 10 pages fail:
result = service.extract_full_text("problematic.pdf")

# result["success"] = True (partial success)
# result["metadata"]["success_pages"] = 8
# result["metadata"]["failed_pages"] = 2
# result["metadata"]["errors"] = ["Failed to extract page 3: ...", ...]
# result["text"] = Combined text from 8 successful pages
```

## Caching

```python
service = PDFExtractionService()

# First extraction - slow
result1 = service.extract_full_text("document.pdf", use_cache=True)
# Extracts, caches result

# Second extraction - instant
result2 = service.extract_full_text("document.pdf", use_cache=True)
# Returns cached result

# Check cache
stats = service.get_cache_stats()
print(f"Cached {stats['cached_files']} files, {stats['total_size_bytes']} bytes")

# Clear cache
service.clear_cache()
```

## Data Classes

### PageContent
```python
from app.utils import PageContent

# Automatically created by extractor
page: PageContent = pages[0]

page.page_number    # int: 1-indexed page number
page.text           # str: extracted text
page.blocks         # List[Dict]: raw PyMuPDF blocks
page.char_count     # int: number of characters
page.line_count     # int: number of lines
```

### ExtractionMetadata
```python
from app.utils import ExtractionMetadata

# Automatically created by extractor
metadata: ExtractionMetadata = ...

metadata.total_pages        # int
metadata.total_chars        # int
metadata.total_lines        # int
metadata.extraction_time    # float (seconds)
metadata.success_pages      # int
metadata.failed_pages       # int
metadata.errors             # List[str]
```

## Common Patterns

### Extract and Process
```python
service = PDFExtractionService()
result = service.extract_full_text("document.pdf")

if result["success"]:
    text = result["text"]
    metadata = result["metadata"]
    
    # Process text (e.g., chunk for embeddings)
    chunks = chunk_text(text, chunk_size=500)
    embeddings = model.embed_batch(chunks)
```

### Extract with Progress
```python
result = service.extract_pages("document.pdf")

total_pages = result["metadata"]["extracted_pages"]
for i, page in enumerate(result["pages"]):
    print(f"Processing page {i+1}/{total_pages}")
    process_page(page["text"])
```

### Extract Specific Pages
```python
# Get pages 5-10
result = service.extract_pages(
    "document.pdf",
    page_range=(5, 10)
)

for page in result["pages"]:
    print(f"Page {page['page']}: {page['char_count']} chars")
```

### Layout-Aware Processing
```python
result = service.extract_with_layout("document.pdf")

# Group blocks by page
by_page = {}
for block in result["blocks"]:
    page = block["page"]
    if page not in by_page:
        by_page[page] = []
    by_page[page].append(block)

# Process each page
for page_num, blocks in by_page.items():
    print(f"Page {page_num}: {len(blocks)} blocks")
```

## Performance Tips

1. **Use Caching for Repeated Documents**
   ```python
   # Enable caching to avoid re-extraction
   result = service.extract_full_text("doc.pdf", use_cache=True)
   ```

2. **Extract Only Needed Pages**
   ```python
   # Instead of full PDF
   result = service.extract_pages("doc.pdf", page_range=(1, 5))
   ```

3. **Use Snippets for Previews**
   ```python
   # Instead of extracting entire page
   snippet = service.extract_text_snippet("doc.pdf", page=1, max_chars=200)
   ```

4. **Extract Metadata Separately**
   ```python
   # Don't extract text if you only need metadata
   result = service.extract_metadata("doc.pdf")
   ```

5. **Use Background Tasks for Large PDFs**
   ```python
   # Offload to background task
   import asyncio
   asyncio.create_task(extract_large_pdf("huge.pdf"))
   ```

## Testing

```bash
# Run extraction tests
pytest tests/test_pdf_extraction.py -v

# Run specific test
pytest tests/test_pdf_extraction.py::TestPDFExtractor::test_extract_text -v

# Run with coverage
pytest tests/test_pdf_extraction.py --cov=app/utils --cov=app/services
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "File not found" | Verify file path is correct and file exists |
| Low extraction quality | Some PDFs have scanned images (need OCR) |
| Slow extraction | Large PDF? Use `extract_pages()` or background task |
| Memory issues | Extraction cache taking too much? Call `clear_cache()` |
| Layout incorrect | Some PDFs require different text extraction mode |

## Extraction Methods Comparison

| Method | Use Case | Speed | Output |
|--------|----------|-------|--------|
| `extract_full_text()` | Get all text | Medium | Single string |
| `extract_pages()` | Process page-by-page | Medium | List of page objects |
| `extract_with_layout()` | Layout analysis | Slower | Blocks with coordinates |
| `extract_metadata()` | Get metadata only | Fast | Metadata dict |
| `extract_text_snippet()` | Preview/summary | Very fast | Short string |

## Next Steps

1. Integrate with embeddings pipeline
2. Implement document chunking
3. Add table detection
4. Add OCR for scanned PDFs
5. Add compression for storage
6. Add async/background processing
7. Add quality metrics

## Resources

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Text Extraction Best Practices](https://pymupdf.readthedocs.io/en/latest/page.html#extracting-text)
- [Coordinate Systems](https://pymupdf.readthedocs.io/en/latest/geometry.html)
