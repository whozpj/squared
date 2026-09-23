"""Application settings, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Squared"
    environment: str = "development"

    # Postgres. Overridden in prod; docker-compose provides a local default.
    database_url: str = "postgresql+psycopg://squared:squared@localhost:5434/squared"

    # Auth (filled in during the auth build step; safe placeholders for now).
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    cors_origins: list[str] = ["http://localhost:5173"]

    # Local receipt-image storage (gitignored).
    upload_dir: str = "uploads"
    ocr_max_workers: int = 2

    # Reminders scheduler (single-process; see DESIGN §8).
    enable_reminders: bool = True
    reminder_interval_hours: int = 24

    # Email (optional; free-tier Resend). Empty key = email is skipped gracefully.
    resend_api_key: str = ""
    email_from: str = "Squared <onboarding@resend.dev>"
    app_url: str = "http://localhost:5173"


    def normalized_database_url(self) -> str:
        """Ensure the psycopg driver is used (Neon/Render give a bare postgresql:// URL)."""
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
