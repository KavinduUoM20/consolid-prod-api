from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class OCAPSettings(BaseSettings):
    """OCAP application settings."""
    
    # Database configuration - reuse same database as dociq
    DATABASE_URL: str
    
    # OCAP Specific Settings (no Azure OpenAI config - using shared LLM connections)
    CONVERSATION_TIMEOUT: int = 3600  # 1 hour in seconds
    MAX_CONVERSATION_TURNS: int = 100
    MAX_ACTIVE_CONNECTIONS: int = 50  # Limit concurrent WebSocket connections
    CONNECTION_CLEANUP_INTERVAL: int = 300  # 5 minutes in seconds
    
    class Config:
        env_prefix = "OCAP_"
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_ocap_settings() -> OCAPSettings:
    """Get OCAP settings instance."""
    return OCAPSettings()
