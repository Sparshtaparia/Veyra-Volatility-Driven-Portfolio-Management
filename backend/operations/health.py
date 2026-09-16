"""Database and migration readiness checks."""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

EXPECTED_SCHEMA_REVISION = "0004_phase6_operations"


def database_readiness(db: Session) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    binding = db.get_bind()
    if inspect(binding).has_table("alembic_version"):
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    else:
        revision = "unversioned"
    return {
        "database": "connected",
        "schema_revision": str(revision),
        "schema_status": (
            "current" if revision == EXPECTED_SCHEMA_REVISION else "migration_required"
        ),
    }
