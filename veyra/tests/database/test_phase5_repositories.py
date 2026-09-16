"""Persistence tests for Phase 5 control, feedback, and backtest state."""

from datetime import date
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.services.backtest_service import BacktestService
from database.repositories.backtest_repo import BacktestRepository
from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.portfolio_control_repo import PortfolioControlRepository
from database.repositories.portfolio_repo import PortfolioRepository
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.feedback.models import FeedbackOutcome, FeedbackUpdate, SystemState
from quant_engine.portfolio.models import ExecutedTrade, OptimizationResult, TradeSide


def seed_correlation_rows(db_session: Session):
    portfolio_id = f"port-{uuid4().hex[:8]}"
    evaluation_id = uuid4()
    PortfolioRepository(db_session).create_portfolio(portfolio_id, "Control", "USD")
    EvaluationRepository(db_session).create_evaluation(
        evaluation_id,
        portfolio_id,
        date(2026, 1, 31),
        EvaluationTrigger.MANUAL,
        EvaluationDecision.REBALANCE,
        EvaluationStatus.COMPLETED,
    )
    return portfolio_id, evaluation_id


def test_portfolio_control_and_feedback_round_trip(db_session: Session) -> None:
    portfolio_id, evaluation_id = seed_correlation_rows(db_session)
    repository = PortfolioControlRepository(db_session)
    result = OptimizationResult(
        as_of_date=date(2026, 1, 31),
        targets=[
            {
                "ticker": "AAA",
                "sector": "TECH",
                "current_weight": 1.0,
                "inverse_volatility_weight": 0.6,
                "target_weight": 0.6,
                "weight_change": -0.4,
            }
        ],
        gross_exposure=0.6,
        net_exposure=0.6,
        cash_weight=0.4,
        expected_volatility=0.1,
        expected_turnover=0.4,
        solver_status="optimal",
    )
    trades = [
        ExecutedTrade(
            ticker="AAA",
            side=TradeSide.SELL,
            quantity=4.0,
            reference_price=100.0,
            execution_price=99.98,
            gross_notional=399.92,
            transaction_cost=0.2,
            slippage_cost=0.08,
            net_cash_change=399.72,
        )
    ]
    repository.create_targets(evaluation_id, portfolio_id, result)
    event = repository.create_rebalance(
        evaluation_id, portfolio_id, result.as_of_date, 1_000.0, 0.4, trades
    )
    repository.create_snapshot(
        portfolio_id,
        evaluation_id,
        result.as_of_date,
        1_000.0,
        400.0,
        0.6,
        0.6,
        [{"ticker": "AAA", "target_weight": 0.6}],
    )
    state = SystemState(
        as_of_date=result.as_of_date,
        volatility_distribution_level=0.02,
        adaptive_threshold=1.0,
        reliability_multiplier=0.8,
        risk_limit=0.6,
        exposure_limit=0.6,
        portfolio_value=1_000.0,
    )
    update = FeedbackUpdate(
        previous_state=state,
        controlled_signal=0.2,
        outcome=FeedbackOutcome(
            observation_date=date(2026, 2, 28),
            portfolio_return=0.01,
            realized_volatility=0.03,
            drawdown=0.02,
            signal_accuracy=0.5,
            transaction_cost=0.2,
        ),
        updated_state=state.model_copy(update={"as_of_date": date(2026, 2, 28)}),
    )
    repository.create_feedback(evaluation_id, portfolio_id, update)
    db_session.commit()

    assert repository.get_targets(evaluation_id)[0].target_weight == 0.6
    assert repository.get_trades(event.event_id)[0].side == "SELL"
    assert repository.latest_snapshot(portfolio_id).cash_value == 400.0
    assert repository.feedback_history(portfolio_id)[0].updated_state["risk_limit"] == 0.6


def test_backtest_round_trip(db_session: Session) -> None:
    dates = pd.date_range("2025-01-01", periods=70, freq="D")
    asset_returns = pd.DataFrame({"AAA": np.full(len(dates), 0.001)}, index=dates)
    weights = pd.DataFrame({"AAA": [0.5, 0.7]}, index=[dates[0], dates[32]])
    benchmark = pd.Series(np.full(len(dates), 0.0002), index=dates)

    backtest_id, result = BacktestService(db_session).run(
        "Persistence", asset_returns, weights, benchmark
    )
    repository = BacktestRepository(db_session)

    assert repository.get(backtest_id).status == "COMPLETED"
    assert len(repository.get_returns(backtest_id)) == len(result.returns)
    assert repository.get_metrics(backtest_id).total_return == result.metrics.total_return
