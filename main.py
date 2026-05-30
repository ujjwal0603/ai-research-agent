import uvicorn
from app import create_app
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    uvicorn.run(
        "app:create_app",
        factory=True,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
