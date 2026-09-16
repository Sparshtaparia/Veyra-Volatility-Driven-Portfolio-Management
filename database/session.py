"""
database/session.py
===================
Synchronous SQLAlchemy session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
