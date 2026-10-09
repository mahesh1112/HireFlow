from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "HireFlow"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "debug"

    # Security
    JWT_SECRET: str = "change-me-in-production-super-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 168  # 7 days
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/hireflow"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis (optional — set to empty string to disable)
    REDIS_URL: str = ""

    # Groq LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "hireflow-resumes"
    PINECONE_ENVIRONMENT: str = "us-east-1"

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf",
                                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    UPLOAD_DIR: str = "/tmp/hireflow_uploads"

    # Screening
    MAX_SHORTLIST_CANDIDATES: int = 20
    MIN_FIT_SCORE_TO_SHOW: int = 0  # show all, reject handled by knockout filters

    class Config:
        # Look for .env in parent directory (project root)
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
