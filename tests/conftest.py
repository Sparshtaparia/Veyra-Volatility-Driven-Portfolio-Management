"""
tests/conftest.py
=================
Pytest fixtures and configuration.

The local suite uses an explicit TEST_DATABASE_URL and defaults to an isolated
in-memory database. PostgreSQL migration behavior is separately verified by
Alembic SQL generation and can be exercised by setting TEST_DATABASE_URL.
"""

import os

# database.session builds its engine during import, so establish a safe test
# configuration before importing any backend or database modules.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.dependencies.auth import CurrentUser, require_auth
from backend.dependencies.db import get_db
from backend.main import app
from database.models import Base

engine = create_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = lambda: CurrentUser(
        user_id="test-user",
        email="test@example.com",
        role="ADMIN",
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
