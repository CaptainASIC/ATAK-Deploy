from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Settings
    APP_NAME: str = "ATAK-Deploy"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    APP_ENV: str = "production"
    
    # Database Settings
    DATABASE_URL: str
    ASYNC_DATABASE_URL: Optional[str] = None
    
    # Redis Settings (Optional)
    REDIS_URL: Optional[str] = None
    REDIS_ENABLED: bool = False
    
    # ATAK Server Settings
    ATAK_SERVER_HOST: str
    ATAK_SERVER_PORT: int = 8089
    ATAK_CERT_DIR: str = "/opt/tak/certs"
    ATAK_FILES_DIR: str = "/opt/tak/certs/files"
    
    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Template Settings
    TEMPLATE_DIR: str = "templates"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment."""
        if self.APP_ENV == "test":
            return f"{self.DATABASE_URL}_test"
        return self.DATABASE_URL

    @property
    def is_development(self) -> bool:
        """Check if the application is running in development mode."""
        return self.APP_ENV.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production mode."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if the application is running in test mode."""
        return self.APP_ENV.lower() == "test"


@lru_cache()
def get_settings() -> Settings:
    """Create and cache settings instance."""
    return Settings()
