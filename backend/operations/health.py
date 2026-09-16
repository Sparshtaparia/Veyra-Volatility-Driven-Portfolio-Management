"""Database and migration readiness checks."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


def _expected_schema_revisions() -> frozenset[str]:
    """Read Alembic heads from the checked-in migration graph, without a DB call."""
    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    script_directory = ScriptDirectory.from_config(Config(str(config_path)))
    return frozenset(script_directory.get_heads())


EXPECTED_SCHEMA_REVISIONS = _expected_schema_revisions()
# Kept as a compatibility export for callers that display the single, linear head.
EXPECTED_SCHEMA_REVISION = next(iter(EXPECTED_SCHEMA_REVISIONS))


def database_readiness(db: Session) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    binding = db.get_bind()
    if inspect(binding).has_table("alembic_version"):
        revisions = {
            str(value)
            for value in db.execute(text("SELECT version_num FROM alembic_version")).scalars()
        }
    else:
        revisions = set()
    revision = ",".join(sorted(revisions)) if revisions else "unversioned"
    return {
        "database": "connected",
        "schema_revision": revision,
        "schema_status": (
            "current" if revisions == EXPECTED_SCHEMA_REVISIONS else "migration_required"
        ),
    }
