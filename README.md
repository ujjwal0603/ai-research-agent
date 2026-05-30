# AI Research Platform Backend

Production-ready FastAPI backend for document ingestion, embedding generation, and semantic search.

## Project Structure

```
.
├── app/
│   ├── __init__.py                 # App factory export
│   ├── main.py                     # FastAPI app creation & configuration
│   ├── config.py                   # Settings management
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py           # Health check endpoints
│   │       ├── upload.py           # Document upload endpoints
│   │       └── retrieval.py        # Search/query endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── upload_service.py       # File upload logic
│   │   ├── retrieval_service.py    # Search logic
│   │   └── embeddings_service.py   # Embedding management
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── models.py               # Embedding model abstractions
│   │   └── processor.py            # Chunk & embed processing
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_store.py         # Vector database abstractions
│   │   └── query_engine.py         # Search execution
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic models
│   └── utils/
│       ├── __init__.py
│       └── logger.py               # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_health.py              # Example tests
├── main.py                         # Entry point
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
├── .env                            # Local environment (gitignored)
├── Dockerfile                      # Container image
├── docker-compose.yml              # Local development stack
├── pytest.ini                      # Testing config
└── .gitignore
```

## Architecture

### Modular Layers

**API Layer** (`app/api/routes/`)
- Clean separation of endpoint logic
- Health checks, document upload, search queries
- Dependency injection for service management

**Service Layer** (`app/services/`)
- Business logic implementation
- Orchestrates embeddings & retrieval
- Handles file validation & processing

**Embeddings Layer** (`app/embeddings/`)
- Pluggable embedding models (OpenAI, custom)
- Document chunking & processing
- Batch embedding operations

**Retrieval Layer** (`app/retrieval/`)
- Vector store abstractions (Pinecone, Weaviate)
- Query execution & result formatting
- Semantic search implementation

**Models** (`app/models/`)
- Pydantic schemas for validation
- Request/response standardization

### Key Features

✅ **Async-first** - Built on FastAPI for high performance
✅ **Modular Design** - Easy to swap embeddings/vector stores
✅ **Configuration Management** - Environment-based settings
✅ **Type Safety** - Full Pydantic validation
✅ **Docker Ready** - Multi-stage Dockerfile + compose
✅ **Logging** - Structured logging to file & console
✅ **Testing** - Pytest structure with fixtures

## Quick Start

### Local Development

1. **Clone & Install**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys & settings
```

3. **Run Development Server**
```bash
python main.py
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Docker Compose (Recommended)

```bash
docker-compose up -d
# FastAPI: http://localhost:8000
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

## API Endpoints

### Health
- `GET /health` - Health status
- `GET /health/ready` - Readiness check

### Documents
- `POST /documents/upload` - Upload document
- `GET /documents/{id}` - Get metadata
- `DELETE /documents/{id}` - Delete document

### Search
- `POST /search/query` - Search documents
- `POST /search/batch-query` - Batch search
- `GET /search/stats/{id}` - Retrieval stats

### Docs
- `GET /docs` - OpenAPI/Swagger UI
- `GET /redoc` - ReDoc documentation

## Configuration

All settings loaded from `.env` file via `pydantic-settings`:

```env
# App
APP_NAME=AI Research Platform
DEBUG=False
ENVIRONMENT=production

# Server
HOST=0.0.0.0
PORT=8000

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Vector Store
VECTOR_STORE_TYPE=pinecone
PINECONE_API_KEY=your_key

# Upload
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=100
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_health.py

# Run by marker
pytest -m unit
```

## Production Deployment

### Environment
```env
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate_with_secrets.token_urlsafe()>
DATABASE_URL=postgresql://user:pass@prod-db:5432/db
```

### Containerization
```bash
docker build -t ai-research:latest .
docker run -p 8000:8000 --env-file .env.prod ai-research:latest
```

### Kubernetes (Optional)
Use the provided Dockerfile with your K8s manifests:
- Liveness probe: `GET /health`
- Readiness probe: `GET /health/ready`

## Implementation Checklist

- [ ] Replace embedding placeholders with actual OpenAI/Anthropic calls
- [ ] Implement file text extraction (PyPDF2, pdfplumber for PDFs)
- [ ] Connect Pinecone or alternative vector store
- [ ] Setup PostgreSQL for document metadata
- [ ] Add authentication (JWT via python-jose)
- [ ] Implement chunking strategy for your documents
- [ ] Add monitoring/metrics
- [ ] Setup CI/CD pipeline

## Dependencies

See `requirements.txt` for full list. Key packages:
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation
- **SQLAlchemy** - ORM
- **Pinecone** - Vector database
- **OpenAI** - Embeddings
- **Pytest** - Testing framework

## Development

### Code Style
```bash
black .          # Format
flake8 app       # Lint
isort .          # Import sorting
mypy app         # Type checking
```

### Adding New Endpoints
1. Create route file in `app/api/routes/`
2. Add model schemas in `app/models/schemas.py`
3. Create service in `app/services/`
4. Include router in `app/main.py`
5. Write tests in `tests/`

## Troubleshooting

**Port already in use**: Change `PORT` in `.env` or kill process on 8000
**Import errors**: Ensure virtualenv activated and `pip install -r requirements.txt` run
**Database connection**: Check `DATABASE_URL` format and ensure PostgreSQL running

## License

MIT
