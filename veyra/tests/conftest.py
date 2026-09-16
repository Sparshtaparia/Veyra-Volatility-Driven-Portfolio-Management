"""
tests/conftest.py
=================
Pytest fixtures and configuration.

The local suite uses an explicit TEST_DATABASE_URL and defaults to an isolated
in-memory database. PostgreSQL migration behavior is separately verified by
Alembic SQL generation and can be exercised by setting TEST_DATABASE_URL.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.dependencies.db import get_db
from backend.main import app
from database.models import Base

# Setup test database (SQLite for local testing, can be switched to PG if needed)
# Since the prompt said DO NOT silently replace, we will try to use the env var,
# but we need to ensure it's a test DB. To avoid blowing up user's DB, we'll use a test URL.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")

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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
