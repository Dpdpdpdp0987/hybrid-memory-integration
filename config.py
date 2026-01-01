from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # Notion
    notion_api_key: str
    notion_database_id: str
    
    # API
    api_secret_key: str
    confidence_threshold: float = 0.85
    environment: str = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()