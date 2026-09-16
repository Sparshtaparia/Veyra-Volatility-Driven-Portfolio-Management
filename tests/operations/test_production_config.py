"""Production settings, pooling, readiness, and API-security tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import database.session as database_session
from backend.middleware.security import ApiSecurityMiddleware
from backend.operations.health import EXPECTED_SCHEMA_REVISION, database_readiness
from backend.operations.scheduler import SchedulerService
from config.settings import Settings


def test_production_requires_postgres_and_strong_api_key() -> None:
    try:
        Settings(
            database_url="sqlite:///:memory:",
            app_env="production",
            api_key="short",
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
        api_key="x" * 32,
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


def test_api_key_middleware_protects_api_but_not_health() -> None:
    app = FastAPI()
    app.add_middleware(ApiSecurityMiddleware, api_prefix="/api/v1", api_key="secret-key")

    @app.get("/api/v1/system/status")
    def protected():
        return {"ok": True}

    @app.get("/health/live")
    def health():
        return {"status": "live"}

    client = TestClient(app)

    assert client.get("/api/v1/system/status").status_code == 401
    assert (
        client.get("/api/v1/system/status", headers={"X-API-Key": "secret-key"}).status_code == 200
    )
    assert client.get("/health/live").status_code == 200


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
