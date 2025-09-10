"""
SQLite fallback configuration for testing without PostgreSQL
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database - use SQLite for testing
    database_url: str = "sqlite:///./claude_web.db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production-abc123xyz789"
    algorithm: str = "HS256"
    access_token_expire_days: int = 30  # Long-lived for personal use

    # Claude Code SDK
    claude_cli_path: str | None = None  # Auto-detect
    claude_timeout_seconds: int = 120  # Based on DISCOVERIES.md

    # Server
    cors_origins: list[str] = ["*"]  # Allow all for dev

    class Config:
        env_file = ".env"


settings = Settings()
