"""
database/session.py
===================
Synchronous SQLAlchemy session management.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings


def build_engine() -> Engine:
    settings = get_settings()
    common: dict[str, object] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("sqlite://"):
        common["connect_args"] = {"check_same_thread": False}
    else:
        common.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
            pool_use_lifo=True,
            connect_args={
                "connect_timeout": settings.database_connect_timeout_seconds,
                "application_name": "veyra-api",
            },
        )
    return create_engine(settings.database_url, **common)


engine = build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


def get_db():
    """
    FastAPI dependency for database sessions.
    Yields a session and ensures it is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
