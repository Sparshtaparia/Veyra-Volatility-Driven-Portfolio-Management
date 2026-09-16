"""Atomic claims and lifecycle persistence for scheduled operations."""

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.operations.models import RunStatus, RunType
from database.models import ScheduledRunModel


class ScheduledRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claim(
        self,
        run_type: RunType,
        portfolio_id: str,
        evaluation_date: date,
        provider: str,
        *,
        lock_timeout_minutes: int,
    ) -> tuple[ScheduledRunModel, bool]:
        now = datetime.utcnow()
        row = ScheduledRunModel(
            run_id=uuid4(),
            run_type=run_type.value,
            portfolio_id=portfolio_id,
            evaluation_date=evaluation_date,
            status=RunStatus.RUNNING.value,
            provider=provider,
            started_at=now,
            stage_timings={},
        )
        try:
            with self.db.begin_nested():
                self.db.add(row)
                self.db.flush()
            self.db.commit()
            self.db.refresh(row)
            return row, True
        except IntegrityError:
            if not self.db.is_active:
                self.db.rollback()

        existing = self.get_for_schedule(run_type, portfolio_id, evaluation_date)
        if existing is None:
            raise RuntimeError("scheduled-run claim conflict could not be resolved")
        cutoff = now - timedelta(minutes=lock_timeout_minutes)
        retryable = existing.status == RunStatus.FAILED.value or (
            existing.status == RunStatus.RUNNING.value and existing.started_at < cutoff
        )
        if not retryable:
            return existing, False
        result = self.db.execute(
            update(ScheduledRunModel)
            .where(
                ScheduledRunModel.run_id == existing.run_id,
                ScheduledRunModel.updated_at == existing.updated_at,
            )
            .values(
                status=RunStatus.RUNNING.value,
                provider=provider,
                started_at=now,
                completed_at=None,
                duration_ms=None,
                stage_timings={},
                error_type=None,
                error_message=None,
                updated_at=now,
            )
        )
        self.db.commit()
        if getattr(result, "rowcount", 0) != 1:
            current = self.get_for_schedule(run_type, portfolio_id, evaluation_date)
            assert current is not None
            return current, False
        self.db.refresh(existing)
        return existing, True

    def attach_evaluation(self, run_id: UUID, evaluation_id: UUID) -> None:
        row = self.get(run_id)
        if row is None:
            raise ValueError("scheduled run not found")
        row.evaluation_id = evaluation_id
        row.updated_at = datetime.utcnow()
        self.db.commit()

    def complete(
        self,
        run_id: UUID,
        duration_ms: float,
        stage_timings: dict[str, float],
    ) -> ScheduledRunModel:
        row = self._required(run_id)
        row.status = RunStatus.COMPLETED.value
        row.completed_at = datetime.utcnow()
        row.duration_ms = duration_ms
        row.stage_timings = stage_timings
        row.error_type = None
        row.error_message = None
        self.db.commit()
        self.db.refresh(row)
        return row

    def fail(
        self,
        run_id: UUID,
        error: Exception,
        duration_ms: float,
        stage_timings: dict[str, float],
    ) -> ScheduledRunModel:
        if not self.db.is_active:
            self.db.rollback()
        row = self._required(run_id)
        row.status = RunStatus.FAILED.value
        row.completed_at = datetime.utcnow()
        row.duration_ms = duration_ms
        row.stage_timings = stage_timings
        row.error_type = type(error).__name__
        row.error_message = str(error)[:2000]
        self.db.commit()
        self.db.refresh(row)
        return row

    def get(self, run_id: UUID) -> ScheduledRunModel | None:
        return self.db.get(ScheduledRunModel, run_id)

    def get_for_schedule(
        self, run_type: RunType, portfolio_id: str, evaluation_date: date
    ) -> ScheduledRunModel | None:
        return self.db.scalar(
            select(ScheduledRunModel).where(
                ScheduledRunModel.run_type == run_type.value,
                ScheduledRunModel.portfolio_id == portfolio_id,
                ScheduledRunModel.evaluation_date == evaluation_date,
            )
        )

    def recent(self, limit: int = 20) -> list[ScheduledRunModel]:
        return list(
            self.db.scalars(
                select(ScheduledRunModel).order_by(ScheduledRunModel.started_at.desc()).limit(limit)
            ).all()
        )

    def counts_by_status(self) -> dict[str, int]:
        rows = self.db.execute(
            select(ScheduledRunModel.status, func.count(ScheduledRunModel.run_id)).group_by(
                ScheduledRunModel.status
            )
        ).all()
        return {status: count for status, count in rows}

    def _required(self, run_id: UUID) -> ScheduledRunModel:
        row = self.get(run_id)
        if row is None:
            raise ValueError("scheduled run not found")
        return row
