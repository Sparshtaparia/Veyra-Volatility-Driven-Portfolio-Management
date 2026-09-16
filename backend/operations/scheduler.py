"""In-process scheduler with database-backed duplicate-run prevention."""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.dependencies.factor_data import get_factor_data_provider
from backend.dependencies.market_data import get_market_data_provider
from backend.operations.pipeline import ScheduledEvaluationPipeline
from config.settings import Settings, get_settings
from database.repositories.portfolio_repo import PortfolioRepository
from database.session import SessionLocal

logger = logging.getLogger("veyra.scheduler")


class SchedulerService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._scheduler = BackgroundScheduler(timezone=self.settings.scheduler_timezone)
        self._lock = threading.Lock()
        self._started = False

    def start(self) -> None:
        if not self.settings.scheduler_enabled:
            logger.info("scheduler_disabled")
            return
        with self._lock:
            if self._started:
                return
            evaluation_trigger = CronTrigger.from_crontab(
                self.settings.scheduled_evaluation_cron,
                timezone=self.settings.scheduler_timezone,
            )
            volatility_trigger = CronTrigger.from_crontab(
                self.settings.scheduled_volatility_cron,
                timezone=self.settings.scheduler_timezone,
            )
            self._scheduler.add_job(
                self.run_full_batch,
                evaluation_trigger,
                id="portfolio-full-evaluation",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=900,
            )
            self._scheduler.add_job(
                self.run_volatility_batch,
                volatility_trigger,
                id="portfolio-volatility-refresh",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=900,
            )
            self._scheduler.start()
            self._started = True
            logger.info(
                "scheduler_started",
                extra={
                    "timezone": self.settings.scheduler_timezone,
                    "evaluation_cron": self.settings.scheduled_evaluation_cron,
                    "volatility_cron": self.settings.scheduled_volatility_cron,
                },
            )

    def stop(self) -> None:
        with self._lock:
            if self._started:
                self._scheduler.shutdown(wait=False)
                self._started = False
                logger.info("scheduler_stopped")

    def run_full_batch(self, evaluation_date: date | None = None) -> None:
        self._run_batch("full", evaluation_date or self._today())

    def run_volatility_batch(self, evaluation_date: date | None = None) -> None:
        self._run_batch("volatility", evaluation_date or self._today())

    def status(self) -> dict[str, object]:
        jobs = []
        if self._started:
            jobs = [
                {
                    "id": job.id,
                    "next_run_time": (job.next_run_time.isoformat() if job.next_run_time else None),
                }
                for job in self._scheduler.get_jobs()
            ]
        return {
            "enabled": self.settings.scheduler_enabled,
            "running": self._started,
            "timezone": self.settings.scheduler_timezone,
            "jobs": jobs,
        }

    def _run_batch(self, kind: str, evaluation_date: date) -> None:
        listing_session = SessionLocal()
        try:
            portfolio_ids = [
                item.id for item in PortfolioRepository(listing_session).list_portfolios()
            ]
        finally:
            listing_session.close()
        provider = get_market_data_provider()
        factor_provider = get_factor_data_provider()
        for portfolio_id in portfolio_ids:
            session = SessionLocal()
            try:
                pipeline = ScheduledEvaluationPipeline(
                    session,
                    provider,
                    factor_provider,
                    settings=self.settings,
                )
                if kind == "full":
                    pipeline.run_full(portfolio_id, evaluation_date)
                else:
                    pipeline.run_volatility_refresh(portfolio_id, evaluation_date)
            except Exception:
                logger.exception(
                    "scheduled_portfolio_failed",
                    extra={
                        "portfolio_id": portfolio_id,
                        "evaluation_date": evaluation_date.isoformat(),
                        "run_kind": kind,
                    },
                )
            finally:
                session.close()

    def _today(self) -> date:
        return datetime.now(ZoneInfo(self.settings.scheduler_timezone)).date()


scheduler_service = SchedulerService()
