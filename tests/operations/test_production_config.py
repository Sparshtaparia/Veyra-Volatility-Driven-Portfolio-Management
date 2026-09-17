"""Production settings, pooling, readiness, and API-security tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import database.session as database_session
from backend.middleware.security import SecurityHeadersMiddleware
from backend.operations.health import EXPECTED_SCHEMA_REVISION, database_readiness
from backend.operations.scheduler import SchedulerService
from config.settings import Settings


def test_production_requires_postgres() -> None:
    try:
        Settings(
            database_url="sqlite:///:memory:",
            app_env="production",
        )
    except ValidationError as error:
        message = str(error)
    else:
        raise AssertionError("invalid production settings were accepted")

    assert "PostgreSQL" in message


def test_production_postgres_pool_configuration(monkeypatch) -> None:
    settings = Settings(
        database_url="postgresql+psycopg2://user:pass@db.example:5432/veyra",
        app_env="production",
        supabase_url="https://project.supabase.co",
        supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
        cors_origins=["https://veyra.example"],
        trusted_hosts=["veyra.example"],
        database_pool_size=7,
        database_max_overflow=3,
    )
    monkeypatch.setattr(database_session, "get_settings", lambda: settings)

    engine = database_session.build_engine()

    assert engine.pool.size() == 7
    assert engine.pool._max_overflow == 3
    engine.dispose()


def test_production_requires_supabase_jwt_configuration_and_deployed_hosts() -> None:
    with pytest.raises(ValidationError, match="SUPABASE_URL and SUPABASE_JWKS_URL"):
        Settings(
            _env_file=None,
            database_url="postgresql://user:pass@db.example/veyra",
            app_env="production",
            cors_origins=["https://app.example"],
            trusted_hosts=["api.example"],
        )

    with pytest.raises(ValidationError, match="deployed origins"):
        Settings(
            database_url="postgresql://user:pass@db.example/veyra",
            app_env="production",
            supabase_url="https://project.supabase.co",
            supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
            cors_origins=["http://localhost:5173"],
            trusted_hosts=["localhost"],
        )


def test_production_rejects_cross_project_jwks_and_insecure_supabase_database() -> None:
    common = {
        "app_env": "production",
        "supabase_url": "https://project.supabase.co",
        "cors_origins": ["https://app.example"],
        "trusted_hosts": ["api.example"],
    }
    with pytest.raises(ValidationError, match="must belong to SUPABASE_URL"):
        Settings(
            database_url="postgresql://user:pass@db.example/veyra",
            supabase_jwks_url="https://other.supabase.co/auth/v1/.well-known/jwks.json",
            **common,
        )
    with pytest.raises(ValidationError, match="sslmode=require"):
        Settings(
            database_url="postgresql://user:pass@pooler.supabase.com/veyra",
            supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
            **common,
        )


def test_database_readiness_checks_connectivity_and_revision() -> None:
    engine = create_engine("sqlite:///:memory:")
    with Session(engine) as session:
        session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64))"))
        session.execute(
            text("INSERT INTO alembic_version VALUES (:revision)"),
            {"revision": EXPECTED_SCHEMA_REVISION},
        )
        session.commit()

        state = database_readiness(session)

    assert state == {
        "database": "connected",
        "schema_revision": EXPECTED_SCHEMA_REVISION,
        "schema_status": "current",
    }


def test_security_headers_middleware_hardens_responses() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/v1/system/status")
    def protected():
        return {"ok": True}

    @app.get("/health/live")
    def health():
        return {"status": "live"}

    client = TestClient(app)

    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert client.get("/health/live").headers["cache-control"] == "no-store"


def test_scheduler_registers_bounded_single_instance_jobs() -> None:
    service = SchedulerService(
        Settings(
            database_url="sqlite:///:memory:",
            app_env="test",
            scheduler_enabled=True,
        )
    )
    try:
        service.start()
        state = service.status()
        assert state["running"] is True
        assert {job["id"] for job in state["jobs"]} == {
            "portfolio-full-evaluation",
            "portfolio-volatility-refresh",
        }
    finally:
        service.stop()
