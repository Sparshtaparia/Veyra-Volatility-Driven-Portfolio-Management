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
"""

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
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
    For Supabase: postgresql+psycopg2://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:6543/postgres?sslmode=require
    """

    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=900, ge=60, le=3600)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    supabase_url: str | None = Field(default=None)
    """Supabase project URL. Example: https://PROJECT_REF.supabase.co"""

    supabase_anon_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY"),
    )
    """Supabase publishable (anon) key. Safe to use in server-side requests."""

    supabase_service_role_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY"),
    )
    """Supabase service-role (secret) key. NEVER expose to frontend."""

    supabase_jwks_url: str | None = Field(default=None)
    """Supabase JWKS endpoint for JWT verification.
    Example: https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
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

    cors_origins: list[str] = ["http://localhost:5173"]
    """Browser origins allowed to call the API."""

    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("VEYRA_API_KEY", "API_KEY"),
    )
    structured_json_logs: bool = True

    market_data_provider: str = "yfinance"
    market_data_fallback_provider: str | None = "yahoo_chart"
    market_data_retry_attempts: int = Field(default=3, ge=1, le=8)
    market_data_backoff_seconds: float = Field(default=0.25, ge=0.0, le=10.0)
    market_data_max_backoff_seconds: float = Field(default=4.0, ge=0.0, le=60.0)
    market_data_timeout_seconds: float = Field(default=20.0, gt=0.0, le=120.0)
    market_data_requests_per_second: float = Field(default=2.0, gt=0.0, le=100.0)
    market_data_max_staleness_days: int = Field(default=5, ge=0, le=30)
    market_data_cache_ttl_seconds: int = Field(default=900, ge=0, le=86400)

    scheduler_enabled: bool = False
    scheduler_timezone: str = "UTC"
    scheduled_evaluation_cron: str = "0 2 * * 1-5"
    scheduled_volatility_cron: str = "0 */6 * * 1-5"
    scheduler_run_lock_timeout_minutes: int = Field(default=120, ge=5, le=1440)

    fama_french_data_path: str | None = None
    """Optional path to a decimal-return five-factor CSV used by Phase 4."""

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
        populate_by_name=True,
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

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.strip()
        allowed = ("postgresql://", "postgresql+psycopg2://", "sqlite://")
        if not value.startswith(allowed):
            raise ValueError("database_url must use PostgreSQL or SQLite SQLAlchemy syntax")
        return value

    @field_validator("market_data_provider", "market_data_fallback_provider")
    @classmethod
    def validate_provider_name(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().lower()
        if normalized not in {"yfinance", "yahoo_chart"}:
            raise ValueError(f"unsupported market-data provider: {value}")
        return normalized

    @field_validator("scheduler_timezone")
    @classmethod
    def validate_scheduler_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown scheduler timezone: {value}") from exc
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.market_data_max_backoff_seconds < self.market_data_backoff_seconds:
            raise ValueError("market-data maximum backoff must be at least the base backoff")
        if self.app_env == "production":
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
                raise ValueError("production requires a PostgreSQL DATABASE_URL")
            supabase_configured = any(
                (self.supabase_url, self.supabase_jwks_url, self.supabase_service_role_key)
            )
            if supabase_configured:
                if not self.supabase_url or not self.supabase_jwks_url:
                    raise ValueError("production requires SUPABASE_URL and SUPABASE_JWKS_URL")
                if not self.supabase_service_role_key:
                    raise ValueError("production requires SUPABASE_SERVICE_ROLE_KEY")
            elif self.api_key is None or len(self.api_key.get_secret_value()) < 32:
                raise ValueError(
                    "production requires complete Supabase auth or a 32-character VEYRA_API_KEY"
                )
            if "*" in self.cors_origins or "*" in self.trusted_hosts:
                raise ValueError("production CORS origins and trusted hosts must be explicit")
            if self.scheduler_enabled and not self.fama_french_data_path:
                raise ValueError("scheduled full evaluation requires FAMA_FRENCH_DATA_PATH")
        return self

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
    # Pydantic supplies required fields from environment variables at runtime.
    return Settings()  # type: ignore[call-arg]
