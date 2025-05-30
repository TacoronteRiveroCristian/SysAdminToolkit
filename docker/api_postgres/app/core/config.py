import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings.

    Uses pydantic-settings to load from environment variables and .env files.
    """
    PROJECT_NAME: str = "PostgreSQL Data Explorer API"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    ACTIVE_API_VERSIONS: List[str] = ["v2"]

    # PostgreSQL settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None # Will be constructed if not provided

    # FastAPI App settings
    FASTAPI_APP_HOST: str = "0.0.0.0"
    FASTAPI_APP_PORT: int = 8000

    # Pagination settings
    DEFAULT_PAGE: int = 1
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Constructs the SQLAlchemy database URL.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()
