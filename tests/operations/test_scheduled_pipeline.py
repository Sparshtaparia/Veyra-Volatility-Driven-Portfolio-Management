"""Scheduled orchestration, idempotency, rollback, and lookahead tests."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.operations.models import RunStatus, RunType
from backend.operations.pipeline import ScheduledEvaluationPipeline
from backend.services.portfolio_upload_service import (
    PortfolioUploadService,
    UploadedHolding,
)
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from config.settings import Settings
from database.models import EvaluationModel, ScheduledRunModel, VolatilityStateModel
from database.repositories.portfolio_control_repo import PortfolioControlRepository
from database.repositories.scheduled_run_repo import ScheduledRunRepository
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MarketDataProvider
from quant_engine.domain import EvaluationTrigger
from quant_engine.regimes.service import RegimeService
from quant_engine.regimes.threshold import FixedThresholdStrategy
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.gjr_garch import GJRGarchEngine
from quant_engine.volatility.service import VolatilityService
from tests.services.test_signal_evaluation_service import (
    FrameFactorProvider,
    IntegrationProvider,
    integration_data,
)


def test_scheduled_full_pipeline_is_end_to_end_and_idempotent(
    db_session: Session,
) -> None:
    bars, factors, as_of_date = integration_data()
    provider = IntegrationProvider(bars)
    portfolio = PortfolioUploadService(db_session, provider).create_portfolio(
        "Scheduled production",
        "USD",
        [
            UploadedHolding(ticker=ticker, quantity=10.0, average_price=100.0)
            for ticker in ("AAA", "BBB", "CCC")
        ],
        as_of_date,
    )
    settings = Settings(database_url="sqlite:///:memory:", app_env="test")

    def volatility_factory(session: Session) -> VolatilityEvaluationService:
        return VolatilityEvaluationService(
            session,
            provider,
            volatility_service=VolatilityService(
                engine=GJRGarchEngine(min_observations=252),
                aggregator=VolatilityAggregator(include_fallbacks_in_aggregation=True),
            ),
            regime_service=RegimeService(threshold_strategy=FixedThresholdStrategy(1.5)),
        )

    pipeline = ScheduledEvaluationPipeline(
        db_session,
        provider,
        FrameFactorProvider(factors),
        settings=settings,
        volatility_factory=volatility_factory,
    )

    first = pipeline.run_full(portfolio.id, as_of_date)
    repeated = pipeline.run_full(portfolio.id, as_of_date)
    refresh = pipeline.run_volatility_refresh(portfolio.id, as_of_date)

    assert first.status is RunStatus.COMPLETED
    assert first.claimed is True
    assert set(first.stage_timings) == {
        "volatility_regime",
        "features_signals_risk",
        "portfolio_optimization",
    }
    assert repeated.run_id == first.run_id
    assert repeated.evaluation_id == first.evaluation_id
    assert repeated.claimed is False
    assert refresh.status is RunStatus.COMPLETED
    assert set(refresh.stage_timings) == {"volatility_regime"}
    assert refresh.evaluation_id != first.evaluation_id
    evaluation = db_session.get(EvaluationModel, first.evaluation_id)
    assert evaluation.trigger is EvaluationTrigger.SCHEDULED
    controls = PortfolioControlRepository(db_session)
    assert controls.get_rebalance(first.evaluation_id) is not None
    assert controls.latest_snapshot(portfolio.id) is not None


def test_duplicate_running_claim_is_prevented(db_session: Session) -> None:
    bars, _, as_of_date = integration_data()
    provider = IntegrationProvider(bars)
    portfolio = PortfolioUploadService(db_session, provider).create_portfolio(
        "Claim",
        "USD",
        [UploadedHolding(ticker="AAA", quantity=1.0, average_price=100.0)],
        as_of_date,
    )
    repository = ScheduledRunRepository(db_session)

    first, claimed = repository.claim(
        RunType.VOLATILITY_REFRESH,
        portfolio.id,
        as_of_date,
        "test",
        lock_timeout_minutes=60,
    )
    second, duplicate_claimed = repository.claim(
        RunType.VOLATILITY_REFRESH,
        portfolio.id,
        as_of_date,
        "test",
        lock_timeout_minutes=60,
    )

    assert claimed is True
    assert duplicate_claimed is False
    assert second.run_id == first.run_id


class FailingVolatilityService:
    def evaluate(self, *_args, **_kwargs):
        raise RuntimeError("provider exhausted")


def test_failed_scheduled_run_rolls_back_and_records_failure(
    db_session: Session,
) -> None:
    bars, factors, as_of_date = integration_data()
    provider = IntegrationProvider(bars)
    portfolio = PortfolioUploadService(db_session, provider).create_portfolio(
        "Failure",
        "USD",
        [UploadedHolding(ticker="AAA", quantity=1.0, average_price=100.0)],
        as_of_date,
    )
    pipeline = ScheduledEvaluationPipeline(
        db_session,
        provider,
        FrameFactorProvider(factors),
        settings=Settings(database_url="sqlite:///:memory:", app_env="test"),
        volatility_factory=lambda _session: FailingVolatilityService(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="provider exhausted"):
        pipeline.run_full(portfolio.id, as_of_date)

    run = db_session.scalar(
        select(ScheduledRunModel).where(ScheduledRunModel.portfolio_id == portfolio.id)
    )
    assert run.status == RunStatus.FAILED.value
    assert run.error_type == "RuntimeError"
    assert db_session.scalars(select(VolatilityStateModel)).all() == []
    assert db_session.execute(select(1)).scalar_one() == 1


class FutureLeakingProvider(MarketDataProvider):
    def get_history(self, ticker: str, start_date: date, end_date: date):
        return [
            MarketBar(
                ticker=ticker,
                timestamp=start_date + timedelta(days=offset),
                open=100.0 + offset,
                high=101.0 + offset,
                low=99.0 + offset,
                close=100.0 + offset,
                volume=1_000.0,
            )
            for offset in range((end_date - start_date).days + 1)
        ]


def test_volatility_history_filters_provider_data_after_as_of(
    db_session: Session,
) -> None:
    as_of_date = date(2026, 1, 10)
    service = VolatilityEvaluationService(
        db_session, FutureLeakingProvider(), history_lookback_days=10
    )

    returns = service._load_returns({"AAA"}, as_of_date)["AAA"]

    assert returns.index.max().date() == as_of_date
