"""Tests for Phase 3D ORM mappings and repositories."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.portfolio_repo import PortfolioRepository
from database.repositories.regime_repo import RegimeRepository
from database.repositories.volatility_repo import VolatilityRepository
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.regimes.models import MarketStressSnapshot
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    MarketRegime,
    MarketVolatilityState,
    VolatilityEstimate,
)


def create_evaluation(db: Session, portfolio_id: str, as_of_date: date):
    evaluation_id = uuid4()
    EvaluationRepository(db).create_evaluation(
        evaluation_id=evaluation_id,
        portfolio_id=portfolio_id,
        evaluation_date=as_of_date,
        trigger=EvaluationTrigger.MANUAL,
        decision=EvaluationDecision.HOLD,
        status=EvaluationStatus.PENDING,
    )
    return evaluation_id


def create_portfolio(db: Session, name: str = "Phase 3") -> str:
    portfolio_id = f"port-{uuid4().hex[:8]}"
    PortfolioRepository(db).create_portfolio(portfolio_id, name, "USD")
    return portfolio_id


def volatility_estimate(ticker: str, as_of_date: date) -> VolatilityEstimate:
    return VolatilityEstimate(
        ticker=ticker,
        timestamp=as_of_date,
        conditional_variance=0.0004,
        conditional_volatility=0.02,
        forecast_volatility=0.021,
        realized_volatility=0.018,
        volatility_ratio=0.02 / 0.018,
        parameters=GARCHParameters(
            omega=0.000001,
            alpha=0.05,
            gamma=0.08,
            beta=0.85,
        ),
        diagnostics=GARCHDiagnostics(
            fit_status=GARCHFitStatus.SUCCESS,
            convergence_status=GARCHConvergenceStatus.CONVERGED,
            observation_count=300,
            log_likelihood=-100.0,
        ),
    )


def stress_snapshot(as_of_date: date, score: float = 1.1) -> MarketStressSnapshot:
    return MarketStressSnapshot(
        timestamp=as_of_date,
        total_asset_count=3,
        eligible_asset_count=3,
        model_fit_count=3,
        fallback_count=0,
        failed_asset_count=0,
        excluded_count=0,
        coverage_ratio=1.0,
        fit_coverage_ratio=1.0,
        fallback_coverage_ratio=0.0,
        median_conditional_volatility=0.02,
        median_realized_volatility=0.018,
        median_volatility_ratio=score,
        aggregate_volatility=0.02,
        stress_score=score,
        volatility_ratio_iqr=0.2,
    )


def market_state(as_of_date: date, score: float = 1.1) -> MarketVolatilityState:
    return MarketVolatilityState(
        as_of_date=as_of_date,
        total_asset_count=3,
        eligible_asset_count=3,
        model_fit_count=3,
        fallback_count=0,
        failed_asset_count=0,
        excluded_count=0,
        coverage_ratio=1.0,
        aggregate_volatility=0.02,
        median_volatility_ratio=score,
        stress_score=score,
        adaptive_threshold=1.2,
        regime=MarketRegime.NORMAL,
        distance_to_threshold=score - 1.2,
    )


def test_volatility_create_many_and_retrieve(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    as_of_date = date(2026, 9, 16)
    evaluation_id = create_evaluation(db_session, portfolio_id, as_of_date)
    repository = VolatilityRepository(db_session)

    created = repository.create_many(
        evaluation_id,
        portfolio_id,
        [volatility_estimate("MSFT", as_of_date), volatility_estimate("AAPL", as_of_date)],
    )
    db_session.commit()
    retrieved = repository.get_by_evaluation(evaluation_id)

    assert len(created) == 2
    assert [row.ticker for row in retrieved] == ["AAPL", "MSFT"]
    assert retrieved[0].persistence == pytest.approx(0.94)
    assert retrieved[0].evaluation.evaluation_id == evaluation_id
    assert retrieved[0].portfolio.id == portfolio_id


def test_volatility_uniqueness_constraint(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    as_of_date = date(2026, 9, 16)
    evaluation_id = create_evaluation(db_session, portfolio_id, as_of_date)
    repository = VolatilityRepository(db_session)
    estimate = volatility_estimate("AAPL", as_of_date)
    repository.create_many(evaluation_id, portfolio_id, [estimate])

    with pytest.raises(IntegrityError):
        repository.create_many(evaluation_id, portfolio_id, [estimate])
    db_session.rollback()


def test_regime_create_retrieve_latest_and_history_order(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    repository = RegimeRepository(db_session)
    dates = [date(2026, 9, 14), date(2026, 9, 16), date(2026, 9, 15)]
    evaluation_ids = []
    for position, as_of_date in enumerate(dates):
        evaluation_id = create_evaluation(db_session, portfolio_id, as_of_date)
        evaluation_ids.append(evaluation_id)
        score = 1.0 + position * 0.05
        repository.create(
            evaluation_id,
            portfolio_id,
            market_state(as_of_date, score),
            stress_snapshot(as_of_date, score),
        )
        db_session.commit()

    latest = repository.get_latest_for_portfolio(portfolio_id)
    history = repository.get_history_for_portfolio(
        portfolio_id,
        through_date=date(2026, 9, 15),
    )

    assert latest is not None
    assert latest.as_of_date == date(2026, 9, 16)
    assert [row.as_of_date for row in history] == [date(2026, 9, 14), date(2026, 9, 15)]
    assert repository.get_by_evaluation(evaluation_ids[0]).evaluation.portfolio_id == portfolio_id


def test_regime_uniqueness_constraint(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session)
    as_of_date = date(2026, 9, 16)
    evaluation_id = create_evaluation(db_session, portfolio_id, as_of_date)
    repository = RegimeRepository(db_session)
    repository.create(
        evaluation_id,
        portfolio_id,
        market_state(as_of_date),
        stress_snapshot(as_of_date),
    )

    with pytest.raises(IntegrityError):
        repository.create(
            evaluation_id,
            portfolio_id,
            market_state(as_of_date),
            stress_snapshot(as_of_date),
        )
    db_session.rollback()


def test_phase3_tables_have_expected_indexes(db_engine) -> None:
    inspector = inspect(db_engine)
    volatility_indexes = {item["name"] for item in inspector.get_indexes("volatility_states")}
    regime_indexes = {item["name"] for item in inspector.get_indexes("regime_states")}

    assert "ix_volatility_states_evaluation_id" in volatility_indexes
    assert "ix_volatility_states_portfolio_date" in volatility_indexes
    assert "ix_volatility_states_ticker_date" in volatility_indexes
    assert "ix_regime_states_evaluation_id" in regime_indexes
    assert "ix_regime_states_portfolio_date" in regime_indexes
