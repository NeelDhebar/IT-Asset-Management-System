"""Application Configuration Manager.

Demonstrates:
- Singleton Pattern (guarantees a single configuration instance across the app lifecycle)
- Profile-based environment handling (DEV, QA, PROD)
- Pydantic Settings validation
"""

import os
from threading import Lock
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema with sensible defaults and environment loading."""

    APP_ENV: str = "dev"
    APP_NAME: str = "Smart IT Asset & Support Ticket Management System"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # Database
    DB_TYPE: str = "sqlite"  # 'sqlite' or 'postgresql'
    DATABASE_URL: str = "sqlite:///./it_assets_dev.db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "it_asset_dev"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "dev_password"

    # Security & Auth
    SECRET_KEY: str = "dev_insecure_secret_key_for_testing_purposes_only_32bytes!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "logs/app.log"

    # CORS
    CORS_ORIGINS: str = (
        "null,http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5501,http://127.0.0.1:5501,"
        "http://localhost:8080,http://127.0.0.1:8080"
    )

    # External API
    EXTERNAL_API_URL: str = "https://worldtimeapi.org/api/timezone/Etc/UTC"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated origin string into list of strings."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(case_sensitive=True, extra="allow")


class ConfigurationManager:
    """Singleton Configuration Manager.

    Ensures only one instance of application settings exists in memory,
    preventing duplicate disk reads and configuration state divergence.
    """

    _instance: Optional["ConfigurationManager"] = None
    _lock: Lock = Lock()
    _settings: Optional[Settings] = None

    def __new__(cls) -> "ConfigurationManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigurationManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        """Determines active profile and loads configuration."""
        env_profile = os.getenv("APP_ENV", "dev").lower()
        env_file = f".env.{env_profile}"

        if not os.path.exists(env_file):
            env_file = ".env" if os.path.exists(".env") else ".env.dev"

        if os.path.exists(env_file):
            self._settings = Settings(_env_file=env_file)
        else:
            self._settings = Settings()

    @property
    def settings(self) -> Settings:
        """Access the loaded settings instance."""
        if self._settings is None:
            self._initialize()
        return self._settings

    @classmethod
    def reset(cls) -> None:
        """Utility for test suites to force reload configuration."""
        with cls._lock:
            cls._instance = None
            cls._settings = None


def get_settings() -> Settings:
    """Convenience accessor to retrieve application settings."""
    return ConfigurationManager().settings
