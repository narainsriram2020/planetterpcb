# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    GEMINI_API_KEY: str
    
    # Database
    DATABASE_URL: str = "sqlite:///./planet_terp_chatbot.db"
    
    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379"
    
    # PlanetTerp API
    PLANETTERP_BASE_URL: str = "https://api.planetterp.com/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model Settings
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Cache TTL (seconds)
    CACHE_TTL: int = 3600
    
    class Config:
        env_file = ".env"

settings = Settings()
