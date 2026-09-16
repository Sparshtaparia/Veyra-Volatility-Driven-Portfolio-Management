"""
backend/dependencies/db.py
==========================
Database dependencies for FastAPI.
"""
from typing import Generator
from sqlalchemy.orm import Session

from database.session import SessionLocal

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
