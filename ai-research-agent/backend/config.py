import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"

# Ensure upload directory exists
UPLOAD_DIR.mkdir(exist_ok=True)

# File upload configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}

# API configuration
API_TITLE = "PDF Upload Service"
API_VERSION = "1.0.0"
