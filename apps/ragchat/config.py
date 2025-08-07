from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class RagchatSettings(BaseSettings):
    DATABASE_URL: str
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "https://consolidator-ai.site"
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "*",
        "X-Forwarded-For",
        "X-Forwarded-Proto", 
        "X-Forwarded-Host",
        "X-Real-IP",
        "X-Requested-With",
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "Cache-Control",
        "X-File-Name"
    ]

    class Config:
        env_prefix = "RAGCHAT_"
        env_file = ".env"  # you can use a different file if you want
        extra = "ignore"  # Ignore extra fields from .env

@lru_cache()
def get_ragchat_settings():
    return RagchatSettings() 