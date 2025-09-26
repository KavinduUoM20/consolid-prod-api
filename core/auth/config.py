from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class AuthSettings(BaseSettings):
    """Authentication settings."""
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production-minimum-32-characters"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    
    # Default Tenant
    DEFAULT_TENANT_SLUG: str = "default"
    
    # Password Requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    
    # Session Settings
    SESSION_CLEANUP_INTERVAL_HOURS: int = 24
    MAX_SESSIONS_PER_USER: int = 10
    
    # Rate Limiting (future use)
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 15
    
    # Default Admin User (for initial setup)
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "Admin123!"
    
    class Config:
        env_prefix = "AUTH_"
        env_file = ".env"
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with direct environment variables if they exist
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", self.JWT_SECRET_KEY)
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", self.JWT_ALGORITHM)
        self.JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(self.JWT_EXPIRE_MINUTES)))
        self.DEFAULT_TENANT_SLUG = os.getenv("DEFAULT_TENANT_SLUG", self.DEFAULT_TENANT_SLUG)


@lru_cache()
def get_auth_settings():
    """Get cached auth settings instance."""
    return AuthSettings()
