from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import API_TITLE, API_VERSION
from routes import router

app = FastAPI(title=API_TITLE, version=API_VERSION)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
def home():
    return {"message": "AI Research Agent Running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)