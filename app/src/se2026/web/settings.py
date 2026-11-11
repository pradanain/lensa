from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SE2026_", env_file=ROOT / ".env", extra="ignore")
    root: Path = ROOT
    census_db: Path = ROOT / "data/processed/se2026.sqlite"
    app_db: Path = ROOT / "data/app/portal.sqlite"
    sls_reference: Path | None = None
    auth_enabled: bool = False
    environment: Literal["local", "production"] = "local"
    allow_web_setup: bool = True
    business_focus_enabled: bool = True
    allowed_hosts: list[str] = ["127.0.0.1", "localhost", "testserver"]
    allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://testserver",
    ]
    secure_cookies: bool = False
    session_hours: int = Field(ge=1, le=24, default=8)
    aggregate_cache_seconds: int = Field(ge=0, le=3600, default=300)
    minimum_contributors: int = Field(ge=5, le=1000, default=5)
    build_index_on_start: bool = True

    @model_validator(mode="after")
    def separate_databases(self):
        if self.environment == "production":
            if not self.secure_cookies or self.allow_web_setup:
                raise ValueError("PRODUCTION_REQUIRES_SECURE_COOKIES_AND_PRIVATE_SETUP")
            if not self.allowed_origins or any(
                not origin.startswith("https://") for origin in self.allowed_origins
            ):
                raise ValueError("PRODUCTION_REQUIRES_HTTPS_ORIGINS")
            if "*" in self.allowed_hosts:
                raise ValueError("PRODUCTION_REQUIRES_EXPLICIT_HOSTS")
        self.root = self.root.resolve()
        self.census_db = self.census_db.resolve()
        self.app_db = self.app_db.resolve()
        if self.app_db == self.census_db:
            raise ValueError("APP_DATABASE_MUST_BE_SEPARATE")
        for protected in (
            self.root / "data/raw",
            self.root / "data/processed",
            self.root / "SE2026_BULUNGAN_WORKSPACE",
            self.root / "archive",
        ):
            if self.app_db == protected or protected in self.app_db.parents:
                raise ValueError("APP_DATABASE_PATH_IS_PROTECTED")
        if self.app_db.is_file() and self.census_db.is_file() and self.app_db.samefile(self.census_db):
            raise ValueError("APP_DATABASE_ALIAS_IS_PROTECTED")
        return self
