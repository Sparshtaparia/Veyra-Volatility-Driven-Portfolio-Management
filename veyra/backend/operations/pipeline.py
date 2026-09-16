"""Idempotent orchestration of the completed Veyra analytical pipeline."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.orm import Session

from backend.operations.metrics import metrics
from backend.operations.models import RunStatus, RunType, ScheduledRunResult
from backend.operations.monitoring import error_monitor
from backend.services.portfolio_control_service import PortfolioControlService
from backend.services.signal_evaluation_service import SignalEvaluationService
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from config.settings import Settings, get_settings
from database.models import ScheduledRunModel
from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.scheduled_run_repo import ScheduledRunRepository
from quant_engine.data.provider import MarketDataProvider
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.factors.provider import FactorDataProvider

logger = logging.getLogger("veyra.scheduler.pipeline")

VolatilityFactory = Callable[[Session], VolatilityEvaluationService]
SignalFactory = Callable[[Session, VolatilityEvaluationService], SignalEvaluationService]
ControlFactory = Callable[[Session], PortfolioControlService]


class ScheduledEvaluationPipeline:
    def __init__(
        self,
        db: Session,
        market_provider: MarketDataProvider,
        factor_provider: FactorDataProvider,
        *,
        settings: Settings | None = None,
        volatility_factory: VolatilityFactory | None = None,
        signal_factory: SignalFactory | None = None,
        control_factory: ControlFactory | None = None,
    ) -> None:
        self.db = db
        self.market_provider = market_provider
        self.factor_provider = factor_provider
        self.settings = settings or get_settings()
        self.runs = ScheduledRunRepository(db)
        self.evaluations = EvaluationRepository(db)
        self.volatility_factory = volatility_factory or (
            lambda session: VolatilityEvaluationService(session, self.market_provider)
        )
        self.signal_factory = signal_factory or (
            lambda session, volatility: SignalEvaluationService(
                session,
                self.market_provider,
                self.factor_provider,
                volatility_evaluation_service=volatility,
            )
        )
        self.control_factory = control_factory or PortfolioControlService
        self.provider_name = getattr(market_provider, "name", type(market_provider).__name__)

    def run_full(self, portfolio_id: str, evaluation_date: date) -> ScheduledRunResult:
        return self._execute(RunType.FULL_EVALUATION, portfolio_id, evaluation_date)

    def run_volatility_refresh(
        self, portfolio_id: str, evaluation_date: date
    ) -> ScheduledRunResult:
        return self._execute(RunType.VOLATILITY_REFRESH, portfolio_id, evaluation_date)

    def _execute(
        self, run_type: RunType, portfolio_id: str, evaluation_date: date
    ) -> ScheduledRunResult:
        run, claimed = self.runs.claim(
            run_type,
            portfolio_id,
            evaluation_date,
            self.provider_name,
            lock_timeout_minutes=self.settings.scheduler_run_lock_timeout_minutes,
        )
        if not claimed:
            metrics.increment("scheduled_runs_skipped")
            logger.info(
                "scheduled_evaluation_skipped",
                extra=self._context(run),
            )
            return self._result(run, claimed=False)

        started = time.perf_counter()
        stage_timings: dict[str, float] = {}
        evaluation_id = self._evaluation_id(run_type, portfolio_id, evaluation_date)
        context = {
            **self._context(run),
            "evaluation_id": str(evaluation_id),
        }
        logger.info("scheduled_evaluation_started", extra=context)
        try:
            self._ensure_evaluation(evaluation_id, portfolio_id, evaluation_date)
            self.runs.attach_evaluation(run.run_id, evaluation_id)
            volatility = self.volatility_factory(self.db)
            self._timed(
                stage_timings,
                "volatility_regime",
                lambda: volatility.evaluate(
                    portfolio_id, evaluation_date, evaluation_id=evaluation_id
                ),
            )
            if run_type is RunType.FULL_EVALUATION:
                signal_service = self.signal_factory(self.db, volatility)
                self._timed(
                    stage_timings,
                    "features_signals_risk",
                    lambda: signal_service.evaluate(
                        portfolio_id, evaluation_date, evaluation_id=evaluation_id
                    ),
                )
                self._timed(
                    stage_timings,
                    "portfolio_optimization",
                    lambda: self.control_factory(self.db).optimize_and_rebalance(
                        portfolio_id, evaluation_id
                    ),
                )
            duration_ms = (time.perf_counter() - started) * 1000.0
            completed = self.runs.complete(run.run_id, duration_ms, stage_timings)
            metrics.increment("scheduled_runs_succeeded")
            metrics.observe_ms(f"scheduled_{run_type.value.lower()}", duration_ms)
            logger.info(
                "scheduled_evaluation_completed",
                extra={
                    **context,
                    "status": RunStatus.COMPLETED.value,
                    "duration_ms": round(duration_ms, 3),
                    "stage_timings": stage_timings,
                },
            )
            return self._result(completed, claimed=True)
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            self.runs.fail(run.run_id, exc, duration_ms, stage_timings)
            metrics.increment("scheduled_runs_failed")
            error_monitor.capture(
                exc,
                {
                    **context,
                    "status": RunStatus.FAILED.value,
                    "evaluation_date": evaluation_date.isoformat(),
                    "duration_ms": round(duration_ms, 3),
                    "stage_timings": stage_timings,
                },
            )
            raise

    def _ensure_evaluation(
        self, evaluation_id: UUID, portfolio_id: str, evaluation_date: date
    ) -> None:
        existing = self.evaluations.get_evaluation(evaluation_id)
        if existing is not None:
            if existing.portfolio_id != portfolio_id or existing.evaluation_date != evaluation_date:
                raise ValueError("scheduled evaluation identity collision")
            return
        self.evaluations.create_evaluation(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            evaluation_date=evaluation_date,
            trigger=EvaluationTrigger.SCHEDULED,
            decision=EvaluationDecision.HOLD,
            status=EvaluationStatus.PENDING,
        )

    @staticmethod
    def _evaluation_id(run_type: RunType, portfolio_id: str, evaluation_date: date) -> UUID:
        return uuid5(
            NAMESPACE_URL,
            f"veyra:{run_type.value}:{portfolio_id}:{evaluation_date.isoformat()}",
        )

    @staticmethod
    def _timed(timings: dict[str, float], stage: str, operation: Callable[[], object]) -> object:
        started = time.perf_counter()
        try:
            return operation()
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            timings[stage] = round(duration_ms, 3)
            metrics.observe_ms(f"pipeline_{stage}", duration_ms)

    @staticmethod
    def _context(run: ScheduledRunModel) -> dict[str, object]:
        return {
            "run_id": str(run.run_id),
            "run_type": run.run_type,
            "portfolio_id": run.portfolio_id,
            "evaluation_date": run.evaluation_date.isoformat(),
            "provider": run.provider,
            "status": run.status,
        }

    @staticmethod
    def _result(run: ScheduledRunModel, *, claimed: bool) -> ScheduledRunResult:
        return ScheduledRunResult(
            run_id=run.run_id,
            run_type=RunType(run.run_type),
            portfolio_id=run.portfolio_id,
            evaluation_date=run.evaluation_date,
            evaluation_id=run.evaluation_id,
            status=RunStatus(run.status),
            claimed=claimed,
            duration_ms=run.duration_ms,
            stage_timings=run.stage_timings,
            error_type=run.error_type,
        )
