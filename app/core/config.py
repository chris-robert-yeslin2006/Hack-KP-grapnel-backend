from pydantic_settings import BaseSettings
from typing import Optional, List
import secrets

class Settings(BaseSettings):
    # Database
    supabase_url: str
    supabase_key: str
    database_url: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = secrets.token_urlsafe(32)
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # API
    api_v1_str: str = "/api/v1"
    project_name: str = "Grapnel Hash Intelligence API"
    version: str = "1.0.0"
    
    # External services
    webhook_secret: str
    max_retry_attempts: int = 3
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    
    # Allowed origins for CORS
    backend_cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000",
    ]

    class Config:
        env_file = ".env"

settings = Settings()