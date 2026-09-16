"""
tests/unit/test_domain.py
=========================
Unit tests for domain models.
"""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from quant_engine.domain import (
    EvaluationDecision,
    EvaluationRequest,
    EvaluationResult,
    EvaluationStatus,
    EvaluationTrigger,
    Portfolio,
    PortfolioHolding,
)


def test_valid_holding():
    holding = PortfolioHolding(ticker="TCS", weight=0.5, quantity=10, market_value=35000.0)
    assert holding.ticker == "TCS"
    assert holding.weight == 0.5


def test_negative_weight_rejected():
    with pytest.raises(ValidationError):
        PortfolioHolding(ticker="TCS", weight=-0.1, quantity=10, market_value=35000.0)


def test_weight_gt_1_rejected():
    with pytest.raises(ValidationError):
        PortfolioHolding(ticker="TCS", weight=1.1, quantity=10, market_value=35000.0)


def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        PortfolioHolding(ticker="TCS", weight=0.5, quantity=-10, market_value=35000.0)


def test_negative_market_value_rejected():
    with pytest.raises(ValidationError):
        PortfolioHolding(ticker="TCS", weight=0.5, quantity=10, market_value=-35000.0)


def test_empty_ticker_rejected():
    with pytest.raises(ValidationError):
        PortfolioHolding(ticker="", weight=0.5, quantity=10, market_value=35000.0)


def test_ticker_normalization():
    holding = PortfolioHolding(ticker=" tcs ", weight=0.5, quantity=10, market_value=35000.0)
    assert holding.ticker == "TCS"


def test_valid_portfolio_empty():
    portfolio = Portfolio(
        portfolio_id="port1", holdings=[], total_value=0.0, as_of_date=date.today()
    )
    assert portfolio.portfolio_id == "port1"


def test_weights_approximately_sum_to_1():
    h1 = PortfolioHolding(ticker="TCS", weight=0.3333333, quantity=10, market_value=33.3)
    h2 = PortfolioHolding(ticker="INFY", weight=0.6666667, quantity=20, market_value=66.7)
    portfolio = Portfolio(
        portfolio_id="port1", holdings=[h1, h2], total_value=100.0, as_of_date=date.today()
    )
    assert portfolio.total_value == 100.0


def test_invalid_portfolio_weights():
    h1 = PortfolioHolding(ticker="TCS", weight=0.5, quantity=10, market_value=50.0)
    h2 = PortfolioHolding(ticker="INFY", weight=0.4, quantity=10, market_value=40.0)
    with pytest.raises(ValidationError):
        Portfolio(
            portfolio_id="port1", holdings=[h1, h2], total_value=90.0, as_of_date=date.today()
        )


def test_valid_evaluation_request():
    req = EvaluationRequest(
        portfolio_id="port1", evaluation_date=date.today(), trigger=EvaluationTrigger.MANUAL
    )
    assert req.portfolio_id == "port1"


def test_invalid_evaluation_request():
    with pytest.raises(ValidationError):
        EvaluationRequest(
            portfolio_id="", evaluation_date=date.today(), trigger=EvaluationTrigger.MANUAL
        )


def test_valid_evaluation_result():
    res = EvaluationResult(
        evaluation_id=uuid4(),
        portfolio_id="port1",
        evaluation_date=date.today(),
        trigger=EvaluationTrigger.MANUAL,
        decision=EvaluationDecision.HOLD,
        status=EvaluationStatus.PENDING,
        created_at=date.today(),
    )
    assert res.status == EvaluationStatus.PENDING


def test_invalid_status():
    with pytest.raises(ValidationError):
        EvaluationResult(
            evaluation_id=uuid4(),
            portfolio_id="port1",
            evaluation_date=date.today(),
            trigger=EvaluationTrigger.MANUAL,
            decision=EvaluationDecision.HOLD,
            status="UNKNOWN",
            created_at=date.today(),
        )
