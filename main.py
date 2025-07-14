# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import router as api_router  # << use this, not api.v1.router
from apps.dociq.db import init_dociq_db
from apps.dociq.config import get_dociq_settings

app = FastAPI(title="Consolidator AI API", version="1.0.0")

# Get settings
settings = get_dociq_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_dociq_db()

app.include_router(api_router) 