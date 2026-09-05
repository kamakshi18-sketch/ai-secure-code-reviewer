import os
from functools import lru_cache
from typing import List, Optional, Any, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    DATABASE_URL: str = Field(..., description="PostgreSQL async connection URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    CHROMADB_URL: str = Field(default="http://localhost:8000", description="ChromaDB connection URL")

    SECRET_KEY: str = Field(..., description="Secret key for JWT signing")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry in days")

    GITHUB_CLIENT_ID: Optional[str] = Field(default=None, description="GitHub OAuth client ID")
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None, description="GitHub OAuth client secret")
    GITHUB_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="GitHub webhook secret")
    GITHUB_APP_ID: Optional[str] = Field(default=None, description="GitHub App ID")
    GITHUB_APP_PRIVATE_KEY: Optional[str] = Field(default=None, description="GitHub App private key")

    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Google API key alias")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    DEFAULT_LLM_PROVIDER: str = Field(default="gemini", description="Default LLM provider: gemini, openai, anthropic")
    DEFAULT_MODEL: str = Field(default="gemini-1.5-flash", description="Default model to use (e.g., gemini-1.5-flash, gemini-1.5-pro)")

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        import os
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend")
    CELERY_TASK_TRACK_STARTED: bool = Field(default=True, description="Track task start")
    CELERY_TASK_TIME_LIMIT: int = Field(default=3600, description="Task time limit in seconds")
    CELERY_WORKER_CONCURRENCY: int = Field(default=4, description="Worker concurrency")

    SCAN_TIMEOUT: int = Field(default=1800, description="Security scan timeout in seconds")
    MAX_PATCH_RETRIES: int = Field(default=3, description="Maximum patch generation retries")
    MAX_FILE_SIZE_MB: int = Field(default=10, description="Maximum file size to scan in MB")
    SUPPORTED_LANGUAGES: Union[List[str], str] = Field(
        default=["python", "javascript", "typescript", "java", "go", "ruby", "php", "csharp"],
        description="Supported programming languages"
    )

    SEMGREP_CONFIG: str = Field(default="auto", description="Semgrep config: auto, p/ci, p/security-audit")
    BANDIT_CONFIG: Optional[str] = Field(default=None, description="Bandit config file path")
    GITLEAKS_CONFIG: Optional[str] = Field(default=None, description="Gitleaks config file path")
    TRIVY_SEVERITY: str = Field(default="HIGH,CRITICAL", description="Trivy severity levels")

    RAG_EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model for RAG")
    RAG_CHUNK_SIZE: int = Field(default=1000, description="Chunk size for document splitting")
    RAG_CHUNK_OVERLAP: int = Field(default=200, description="Chunk overlap for document splitting")
    RAG_TOP_K: int = Field(default=5, description="Number of documents to retrieve")
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Minimum similarity threshold")

    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: Union[List[str], str] = Field(default=["*"], description="Allowed hosts")

    @field_validator("SUPPORTED_LANGUAGES", "CORS_ORIGINS", "ALLOWED_HOSTS", mode="after")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if v is not None else []

    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = Field(default=None, description="OTLP endpoint for tracing")

    BACKEND_URL: str = Field(default="http://localhost:8001", description="Public URL of this backend")
    GITHUB_API_URL: str = Field(default="https://api.github.com", description="GitHub API base URL")
    GITHUB_RAW_URL: str = Field(default="https://raw.githubusercontent.com", description="GitHub raw content URL")

    REPORT_OUTPUT_DIR: str = Field(default="/tmp/reports", description="Directory for generated reports")
    TEMP_DIR: str = Field(default="/tmp/ai-reviewer", description="Temporary directory for clones and patches")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()