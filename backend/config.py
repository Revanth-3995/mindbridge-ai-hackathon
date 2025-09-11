"""
Configuration management using Pydantic BaseSettings with .env support.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
	# Minimal required
	PROJECT_NAME: str = Field("MindBridge Backend", env="PROJECT_NAME")
	API_V1_STR: str = Field("/api", env="API_V1_STR")
	DATABASE_URL: str = Field("sqlite:///./test.db", env="DATABASE_URL")
	ML_SERVICE_URL: str = Field("http://localhost:9000", env="ML_SERVICE_URL")

	# Existing fields referenced elsewhere
	SQLITE_URL: str = Field("sqlite:///./dev.db", env="SQLITE_URL")
	USE_SQLITE_FALLBACK: bool = Field(True, env="USE_SQLITE_FALLBACK")
	REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")
	SECRET_KEY: str = Field("changeme", env="SECRET_KEY")
	ALGORITHM: str = Field("HS256", env="ALGORITHM")
	ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
	REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
	CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
	CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
	SOCKETIO_CORS_ALLOWED_ORIGINS: str = Field("http://localhost:3000,http://localhost:8080", env="SOCKETIO_CORS_ALLOWED_ORIGINS")
	APP_NAME: str = Field("Mind Bridge AI", env="APP_NAME")
	APP_VERSION: str = Field("1.0.0", env="APP_VERSION")
	DEBUG: bool = Field(True, env="DEBUG")
	HOST: str = Field("0.0.0.0", env="HOST")
	PORT: int = Field(8000, env="PORT")
	DB_POOL_SIZE: int = Field(10, env="DB_POOL_SIZE")
	DB_MAX_OVERFLOW: int = Field(20, env="DB_MAX_OVERFLOW")
	DB_POOL_TIMEOUT: int = Field(30, env="DB_POOL_TIMEOUT")
	DB_POOL_RECYCLE: int = Field(1800, env="DB_POOL_RECYCLE")
	CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"], env="CORS_ORIGINS")
	MAX_FILE_SIZE: int = Field(10 * 1024 * 1024, env="MAX_FILE_SIZE")
	UPLOAD_DIR: str = Field("uploads", env="UPLOAD_DIR")
	LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
	LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
	BCRYPT_ROUNDS: int = Field(12, env="BCRYPT_ROUNDS")
	RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
	RATE_LIMIT_WINDOW: int = Field(60, env="RATE_LIMIT_WINDOW")
	LOGIN_RATE_LIMIT_REQUESTS: int = Field(5, env="LOGIN_RATE_LIMIT_REQUESTS")
	LOGIN_RATE_LIMIT_WINDOW: int = Field(60, env="LOGIN_RATE_LIMIT_WINDOW")

	class Config:
		env_file = ".env"
		env_file_encoding = "utf-8"


settings = Settings()

# Ensure upload directory exists
try:
	os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except Exception:
	pass
