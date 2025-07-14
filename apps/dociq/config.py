from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class DociqSettings(BaseSettings):
    DATABASE_URL: str
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    class Config:
        env_prefix = "DOCIQ_"
        env_file = ".env"  # you can use a different file if you want
        extra = "ignore"  # Ignore extra fields from .env

@lru_cache()
def get_dociq_settings():
    return DociqSettings()