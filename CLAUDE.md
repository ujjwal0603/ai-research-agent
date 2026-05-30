# AI Research Platform - Project Documentation

## Overview
Production-ready FastAPI backend for AI research platform with document ingestion, semantic search, and embeddings management.

## Architecture Principles

1. **Modular Layers** - Clean separation of concerns:
   - API Routes (endpoints)
   - Services (business logic)
   - Embeddings (vector operations)
   - Retrieval (search)
   - Models (data schemas)

2. **Pluggable Components** - Easily swap implementations:
   - `EmbeddingModel` abstract class for different embedding providers
   - `VectorStore` abstract class for different vector databases
   - Service injection pattern for testability

3. **Configuration Management** - Environment-driven settings via pydantic-settings
   - Load from `.env` file
   - Override via environment variables
   - Type-safe access

## Key Files & Responsibilities

### Core Application (`app/`)
- **main.py** - FastAPI factory function, middleware setup, route registration
- **config.py** - Settings management with pydantic-settings (environment variables)
- **__init__.py** - App export for clean imports

### API Routes (`app/api/routes/`)
- **health.py** - Health checks (status, readiness probes)
- **upload.py** - Document upload endpoints with validation
- **retrieval.py** - Search/query endpoints

Each route module:
- Has its own router with prefix
- Uses dependency injection for services
- Includes comprehensive error handling
- Structured logging

### Services (`app/services/`)
Business logic layer - no direct database access in routes

- **upload_service.py** - File validation, storage, text extraction
- **retrieval_service.py** - Execute searches using QueryEngine
- **embeddings_service.py** - Coordinate embedding generation & storage

### Embeddings (`app/embeddings/`)
- **models.py** - `EmbeddingModel` abstract base, `OpenAIEmbedding` implementation
- **processor.py** - `EmbeddingProcessor` handles document chunking & batch embedding

Current placeholders - implement actual API calls to OpenAI/Anthropic

### Retrieval (`app/retrieval/`)
- **vector_store.py** - `VectorStore` abstract base, `PineconeVectorStore` implementation
- **query_engine.py** - `QueryEngine` executes searches, formats results

Current placeholders - connect to Pinecone/Weaviate/Qdrant

### Models (`app/models/schemas.py`)
Pydantic models for:
- `Document` - document metadata
- `UploadResponse` - POST /upload response
- `QueryRequest`/`QueryResponse` - search request/response
- `HealthCheck` - health endpoint response

### Utilities (`app/utils/`)
- **logger.py** - Structured logging setup (console + file handlers)

## Configuration

All settings in `.env` file (gitignored, copy from `.env.example`):
- App metadata (name, version, debug)
- Server (host, port, log level)
- Database URLs (PostgreSQL, Redis)
- API keys (OpenAI, Pinecone, etc.)
- Upload constraints
- Embedding model settings
- CORS origins

Loaded via `get_settings()` singleton cached with `@lru_cache`.

## Deployment

### Docker
- Multi-stage build for size optimization
- Non-root user (security)
- Health check configured
- Ports: 8000 (FastAPI), 5432 (PostgreSQL), 6379 (Redis)

### Docker Compose
Full stack: FastAPI + PostgreSQL + Redis with health checks

## Testing

- **pytest.ini** - Configuration (test paths, async mode, markers)
- **tests/test_health.py** - Example health check tests
- Uses `TestClient` from fastapi.testclient

Run: `pytest` or `pytest -v`

## Implementation Checklist

Priority order:

1. **Embeddings Integration**
   - Replace OpenAI placeholder with real API calls
   - Implement batch embedding for performance
   - Add caching for duplicate queries

2. **Vector Store Connection**
   - Connect Pinecone/Qdrant/Weaviate
   - Test vector search quality
   - Handle vector ID mapping

3. **File Processing**
   - Implement text extraction (PyPDF2 for PDFs)
   - Add chunking strategy (token-based, semantic, etc.)
   - Handle multiple file types

4. **Database**
   - Create SQLAlchemy models for document metadata
   - Setup Alembic migrations
   - Implement crud operations

5. **Authentication**
   - Add JWT token generation (python-jose)
   - Implement auth dependency
   - Protect upload/search endpoints

6. **Testing**
   - Add tests for each service
   - Integration tests with real embeddings
   - Load testing for search performance

## Patterns

### Dependency Injection
```python
def get_retrieval_service() -> RetrievalService:
    # Initialize with dependencies
    pass

@router.post("/search")
async def search(retrieval_service = Depends(get_retrieval_service)):
    pass
```

### Error Handling
```python
try:
    result = operation()
    logger.info(f"Success: {result}")
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.error(f"Failure: {e}")
    raise HTTPException(500, "Operation failed")
```

### Service Usage
```python
# Services handle business logic
service = RetrievalService(query_engine, embedding_processor)
response = service.search(query="...")

# Routes call services
@router.post("/search")
async def search(retrieval_service = Depends(get_retrieval_service)):
    return retrieval_service.search(request.query)
```

## Performance Considerations

- **Async throughout** - All endpoints are async
- **Batch operations** - Embedding processor supports batch embedding
- **Caching** - Redis available in docker-compose
- **Connection pooling** - SQLAlchemy handles DB connections
- **Structured logging** - Minimal overhead

## Security Notes

- `.env` file gitignored (never commit secrets)
- CORS whitelist configured
- JWT available via python-jose (implement!)
- Upload size limits enforced
- File type whitelist enforced
- Non-root Docker user
- Input validation via Pydantic

## Known Placeholders

- `EmbeddingModel.embed_text()` - Returns dummy vectors
- `EmbeddingModel.embed_batch()` - Returns dummy vectors
- `VectorStore.search()` - Returns empty list
- `UploadService.extract_text()` - Returns empty string
- Service dependency injection in routes (need actual initialization)

Replace these with real implementations when connecting to actual services.
