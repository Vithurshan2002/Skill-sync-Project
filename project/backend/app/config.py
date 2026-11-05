from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DATABASE = "skillsync_integration_test"


def require_integration_database(dsn: str | URL) -> URL:
    """Fail closed before connecting, including when DATABASE_URL overrides .env."""
    url = make_url(dsn)
    if url.drivername != "postgresql+psycopg" or url.database != INTEGRATION_DATABASE:
        raise ValueError(
            "This testing checkout can only use PostgreSQL database "
            f"'{INTEGRATION_DATABASE}'. Existing project databases are blocked."
        )
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_env: str = "local"
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = INTEGRATION_DATABASE
    db_user: str = "skillsync_integration_app"
    db_password: str = ""
    database_url: str | None = None
    token_ttl_minutes: int = Field(default=480, ge=5, le=10080)
    ai_enabled: bool = True
    ai_base_url: str = "http://127.0.0.1:8102"
    ai_timeout_seconds: float = Field(default=15, gt=0, le=60)

    def database_dsn(self) -> str | URL:
        return require_integration_database(
            self.database_url
            or URL.create(
                "postgresql+psycopg",
                username=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
            )
        )
