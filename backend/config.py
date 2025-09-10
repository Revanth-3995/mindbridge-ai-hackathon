"""
Configuration management for the FastAPI application.
Handles environment variables and application settings.
"""

from decouple import config
from typing import Optional
import os
import secrets

class Settings:
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    DATABASE_URL: str = config(
        "DATABASE_URL", 
        default="postgresql://mindbridge_user:dev_password_123@localhost:5432/mindbridge_db"
    )
    SQLITE_URL: str = config("SQLITE_URL", default="sqlite:///./dev.db")
    USE_SQLITE_FALLBACK: bool = config("USE_SQLITE_FALLBACK", default=True, cast=bool)
    
    # Redis Configuration
    REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379")
    
    # JWT Configuration
    SECRET_KEY: str = config("SECRET_KEY", default=secrets.token_urlsafe(32))
    ALGORITHM: str = config("ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
    REFRESH_TOKEN_EXPIRE_DAYS: int = config("REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int)
    
    # Celery Configuration
    CELERY_BROKER_URL: str = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
    
    # Socket.IO Configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS: str = config(
        "SOCKETIO_CORS_ALLOWED_ORIGINS", 
        default="http://localhost:3000,http://localhost:8080"
    )
    
    # Application Configuration
    APP_NAME: str = config("APP_NAME", default="Mind Bridge AI")
    APP_VERSION: str = config("APP_VERSION", default="1.0.0")
    DEBUG: bool = config("DEBUG", default=True, cast=bool)
    HOST: str = config("HOST", default="0.0.0.0")
    PORT: int = config("PORT", default=8000, cast=int)
    
    # Database Pool Configuration
    DB_POOL_SIZE: int = config("DB_POOL_SIZE", default=10, cast=int)
    DB_MAX_OVERFLOW: int = config("DB_MAX_OVERFLOW", default=20, cast=int)
    DB_POOL_TIMEOUT: int = config("DB_POOL_TIMEOUT", default=30, cast=int)
    DB_POOL_RECYCLE: int = config("DB_POOL_RECYCLE", default=3600, cast=int)
    
    # CORS Configuration
    CORS_ORIGINS: list = config(
        "CORS_ORIGINS", 
        default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000",
        cast=lambda v: [s.strip() for s in v.split(",")]
    )
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = config("MAX_FILE_SIZE", default=10485760, cast=int)  # 10MB
    UPLOAD_DIR: str = config("UPLOAD_DIR", default="uploads")
    
    # Logging Configuration
    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
    LOG_FILE: Optional[str] = config("LOG_FILE", default=None)
    
    # Security Configuration
    BCRYPT_ROUNDS: int = config("BCRYPT_ROUNDS", default=12, cast=int)
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = config("RATE_LIMIT_REQUESTS", default=100, cast=int)
    RATE_LIMIT_WINDOW: int = config("RATE_LIMIT_WINDOW", default=60, cast=int)
    LOGIN_RATE_LIMIT_REQUESTS: int = config("LOGIN_RATE_LIMIT_REQUESTS", default=5, cast=int)
    LOGIN_RATE_LIMIT_WINDOW: int = config("LOGIN_RATE_LIMIT_WINDOW", default=60, cast=int)
    
    def __init__(self):
        """Initialize settings and create necessary directories."""
        # Create upload directory if it doesn't exist
        if not os.path.exists(self.UPLOAD_DIR):
            os.makedirs(self.UPLOAD_DIR, exist_ok=True)
    
    @property
    def database_url(self) -> str:
        """Get the appropriate database URL based on configuration."""
        if self.USE_SQLITE_FALLBACK:
            try:
                # Try to connect to PostgreSQL first
                import psycopg2
                from urllib.parse import urlparse
                parsed = urlparse(self.DATABASE_URL)
                psycopg2.connect(
                    host=parsed.hostname,
                    port=parsed.port,
                    database=parsed.path[1:],
                    user=parsed.username,
                    password=parsed.password
                )
                return self.DATABASE_URL
            except Exception:
                # Fallback to SQLite
                return self.SQLITE_URL
        return self.DATABASE_URL

# Global settings instance
settings = Settings()
