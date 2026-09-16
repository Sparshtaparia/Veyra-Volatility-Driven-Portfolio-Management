"""Tests for Phase 3D application orchestration and transaction behavior."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.exceptions import VolatilityPersistenceError
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from database.models import EvaluationModel, RegimeStateModel, VolatilityStateModel
from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.portfolio_repo import PortfolioRepository
from database.repositories.regime_repo import RegimeRepository
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MarketDataProvider
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import MarketStressSnapshot
from quant_engine.regimes.service import RegimeService
from quant_engine.regimes.threshold import FixedThresholdStrategy
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    MarketRegime,
    MarketVolatilityState,
    VolatilityEstimate,
)
from quant_engine.volatility.service import VolatilityServiceResult

AS_OF_DATE = date(2026, 9, 16)


class StaticProvider(MarketDataProvider):
    def get_history(self, ticker: str, start_date: date, end_date: date):
        return [
            MarketBar(
                ticker=ticker,
                timestamp=AS_OF_DATE - timedelta(days=1),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1_000.0,
            ),
            MarketBar(
                ticker=ticker,
                timestamp=AS_OF_DATE,
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1_000.0,
            ),
        ]


class StubVolatilityService:
    def __init__(self, result: VolatilityServiceResult | Exception):
        self.result = result
        self.aggregator = VolatilityAggregator()

    def evaluate(self, returns_by_ticker, *, as_of_date):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class CapturingRegimeService:
    def __init__(self, state: MarketVolatilityState):
        self.state = state
        self.history = None

    def evaluate(self, current, history):
        self.history = list(history)
        return self.state


def create_portfolio(db: Session, ticker_count: int = 4) -> str:
    repository = PortfolioRepository(db)
    portfolio_id = f"port-{uuid4().hex[:8]}"
    repository.create_portfolio(portfolio_id, "Phase 3D", "USD")
    for position in range(ticker_count):
        repository.add_holding(
            portfolio_id,
            f"T{position}",
            1.0,
            100.0,
            100.0,
            100.0,
            1.0 / ticker_count,
        )
    return portfolio_id


def estimate(
    ticker: str,
    *,
    fit_status: GARCHFitStatus = GARCHFitStatus.SUCCESS,
) -> VolatilityEstimate:
    parameters = None
    convergence = GARCHConvergenceStatus.NOT_APPLICABLE
    if fit_status is GARCHFitStatus.SUCCESS:
        parameters = GARCHParameters(omega=0.000001, alpha=0.05, gamma=0.08, beta=0.85)
        convergence = GARCHConvergenceStatus.CONVERGED
    return VolatilityEstimate(
        ticker=ticker,
        timestamp=AS_OF_DATE,
        conditional_variance=0.0004,
        conditional_volatility=0.02,
        forecast_volatility=0.021,
        realized_volatility=0.018,
        volatility_ratio=1.1,
        parameters=parameters,
        diagnostics=GARCHDiagnostics(
            fit_status=fit_status,
            convergence_status=convergence,
            observation_count=300,
        ),
    )


def snapshot(
    *,
    total: int = 4,
    eligible: int = 3,
    fit_count: int = 3,
    fallback_count: int = 0,
    failed_count: int = 1,
    score: float = 1.1,
) -> MarketStressSnapshot:
    return MarketStressSnapshot(
        timestamp=AS_OF_DATE,
        total_asset_count=total,
        eligible_asset_count=eligible,
        model_fit_count=fit_count,
        fallback_count=fallback_count,
        failed_asset_count=failed_count,
        excluded_count=total - eligible,
        coverage_ratio=eligible / total,
        fit_coverage_ratio=fit_count / total,
        fallback_coverage_ratio=fallback_count / total,
        median_conditional_volatility=0.02,
        median_realized_volatility=0.018,
        median_volatility_ratio=score,
        aggregate_volatility=0.02,
        stress_score=score,
        volatility_ratio_iqr=0.1,
    )


def result_with_partial_failure() -> VolatilityServiceResult:
    return VolatilityServiceResult(
        estimates=[estimate("T0"), estimate("T1"), estimate("T2")],
        failed_tickers={"T3": "fit failed"},
        market_stress_snapshot=snapshot(),
    )


def fixed_regime_service() -> RegimeService:
    return RegimeService(threshold_strategy=FixedThresholdStrategy(1.2))


def persisted_state(as_of_date: date, score: float) -> MarketVolatilityState:
    return MarketVolatilityState(
        as_of_date=as_of_date,
        total_asset_count=4,
        eligible_asset_count=3,
        model_fit_count=3,
        fallback_count=0,
        failed_asset_count=1,
        excluded_count=1,
        coverage_ratio=0.75,
        aggregate_volatility=0.02,
        median_volatility_ratio=score,
        stress_score=score,
        adaptive_threshold=1.2,
        regime=MarketRegime.NORMAL,
        distance_to_threshold=score - 1.2,
    )


def persisted_snapshot(as_of_date: date, score: float) -> MarketStressSnapshot:
    value = snapshot(score=score).model_copy(update={"timestamp": as_of_date})
    return value


def create_evaluation(db: Session, portfolio_id: str, as_of_date: date):
    return EvaluationRepository(db).create_evaluation(
        uuid4(),
        portfolio_id,
        as_of_date,
        EvaluationTrigger.MANUAL,
        EvaluationDecision.HOLD,
        EvaluationStatus.COMPLETED,
    )


def test_success_persists_partial_failure_and_is_idempotent(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    evaluation_id = uuid4()
    volatility_service = StubVolatilityService(result_with_partial_failure())
    service = VolatilityEvaluationService(
        db_session,
        StaticProvider(),
        volatility_service=volatility_service,
        regime_service=fixed_regime_service(),
    )

    first = service.evaluate(portfolio_id, AS_OF_DATE, evaluation_id=evaluation_id)
    second = service.evaluate(portfolio_id, AS_OF_DATE, evaluation_id=evaluation_id)

    assert first == second
    assert first.evaluation_id == evaluation_id
    assert len(first.asset_volatility) == 3
    assert db_session.scalar(select(EvaluationModel.status)) is EvaluationStatus.COMPLETED
    assert len(db_session.scalars(select(VolatilityStateModel)).all()) == 3
    assert len(db_session.scalars(select(RegimeStateModel)).all()) == 1


def test_fallback_estimate_is_persisted_but_excluded_from_regime_coverage(
    db_session: Session,
) -> None:
    portfolio_id = create_portfolio(db_session)
    estimates = [
        estimate("T0"),
        estimate("T1"),
        estimate("T2"),
        estimate("T3", fit_status=GARCHFitStatus.FALLBACK),
    ]
    result = VolatilityServiceResult(
        estimates=estimates,
        failed_tickers={},
        market_stress_snapshot=snapshot(fallback_count=1, failed_count=0),
    )
    service = VolatilityEvaluationService(
        db_session,
        StaticProvider(),
        volatility_service=StubVolatilityService(result),
        regime_service=fixed_regime_service(),
    )

    response = service.evaluate(portfolio_id, AS_OF_DATE)

    assert len(response.asset_volatility) == 4
    assert sum(item.used_fallback for item in response.asset_volatility) == 1
    assert response.market_regime.eligible_asset_count == 3
    assert response.market_regime.coverage_ratio == pytest.approx(0.75)


def test_insufficient_coverage_marks_evaluation_failed(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    error = InsufficientCoverageError(2, 4, 3, 0.5)
    service = VolatilityEvaluationService(
        db_session,
        StaticProvider(),
        volatility_service=StubVolatilityService(error),
        regime_service=fixed_regime_service(),
    )

    with pytest.raises(InsufficientCoverageError):
        service.evaluate(portfolio_id, AS_OF_DATE)

    assert not db_session.scalars(select(VolatilityStateModel)).all()
    assert not db_session.scalars(select(RegimeStateModel)).all()


def test_history_is_chronological_and_excludes_future_rows(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    repository = RegimeRepository(db_session)
    dates = [
        AS_OF_DATE - timedelta(days=2),
        AS_OF_DATE + timedelta(days=1),
        AS_OF_DATE - timedelta(days=1),
    ]
    for position, historical_date in enumerate(dates):
        evaluation = create_evaluation(db_session, portfolio_id, historical_date)
        score = 1.0 + position * 0.01
        repository.create(
            evaluation.evaluation_id,
            portfolio_id,
            persisted_state(historical_date, score),
            persisted_snapshot(historical_date, score),
        )
        db_session.commit()

    capturing = CapturingRegimeService(persisted_state(AS_OF_DATE, 1.1))
    service = VolatilityEvaluationService(
        db_session,
        StaticProvider(),
        volatility_service=StubVolatilityService(result_with_partial_failure()),
        regime_service=capturing,
    )

    service.evaluate(portfolio_id, AS_OF_DATE)

    assert [item.timestamp for item in capturing.history] == [
        AS_OF_DATE - timedelta(days=2),
        AS_OF_DATE - timedelta(days=1),
    ]


def test_regime_persistence_failure_rolls_back_asset_states(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    service = VolatilityEvaluationService(
        db_session,
        StaticProvider(),
        volatility_service=StubVolatilityService(result_with_partial_failure()),
        regime_service=fixed_regime_service(),
    )

    def fail_regime_write(*args, **kwargs):
        raise RuntimeError("database write failed")

    service.regime_repo.create = fail_regime_write
    with pytest.raises(VolatilityPersistenceError):
        service.evaluate(portfolio_id, AS_OF_DATE)

    assert not db_session.scalars(select(VolatilityStateModel)).all()
    assert not db_session.scalars(select(RegimeStateModel)).all()
