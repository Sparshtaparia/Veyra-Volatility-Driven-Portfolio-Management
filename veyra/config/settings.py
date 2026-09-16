"""
config/settings.py
==================
Central application configuration loaded from environment variables.

All settings are read from environment variables (or a .env file).
No credentials or secrets are hardcoded.

Usage
-----
    from config.settings import get_settings

    settings = get_settings()
    print(settings.database_url)
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Environment variables are the canonical source of truth.
    A `.env` file in the working directory is loaded as a fallback
    (useful for local development).
    """

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str
    """Full SQLAlchemy connection string.
    Example: postgresql+psycopg2://veyra:veyra@localhost:5432/veyra
    """

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_env: str = "development"
    """Runtime environment: development | staging | production"""

    log_level: str = "INFO"
    """Python logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL"""

    api_prefix: str = "/api/v1"
    """URL prefix for all API routes."""

    # ------------------------------------------------------------------
    # Business defaults
    # ------------------------------------------------------------------
    default_currency: str = "INR"
    """Default currency for portfolios that do not specify one."""

    default_evaluation_frequency: str = "MONTHLY"
    """
    Default evaluation frequency.

    NOTE: Veyra separates EVALUATION frequency from REBALANCE frequency.
    An evaluation may result in HOLD — no trade is executed.

    Future trigger types will include:
        PERIODIC, MANUAL, PORTFOLIO_CHANGE, PRICE_THRESHOLD

    Phase 1 supports: SCHEDULED, EVENT_DRIVEN, MANUAL
    """

    # ------------------------------------------------------------------
    # Portfolio constraints
    # ------------------------------------------------------------------
    max_single_asset_weight: float = 1.0
    """Maximum allocation to a single asset as a fraction (0–1)."""

    min_single_asset_weight: float = 0.0
    """Minimum allocation to a single asset as a fraction (0–1)."""

    # ------------------------------------------------------------------
    # Pydantic-settings configuration
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # Silently drop unknown env vars
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {v!r}")
        return upper

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        lower = v.lower()
        if lower not in allowed:
            raise ValueError(f"app_env must be one of {allowed}, got {v!r}")
        return lower

    @field_validator("max_single_asset_weight")
    @classmethod
    def validate_max_weight(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("max_single_asset_weight must be between 0 and 1")
        return v

    @field_validator("min_single_asset_weight")
    @classmethod
    def validate_min_weight(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("min_single_asset_weight must be between 0 and 1")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Using lru_cache ensures settings are loaded only once per process,
    avoiding repeated file/env reads. Tests can override this by
    clearing the cache: get_settings.cache_clear().
    """
    return Settings()
