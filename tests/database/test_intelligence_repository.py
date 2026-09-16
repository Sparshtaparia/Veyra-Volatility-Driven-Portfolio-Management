"""Persistence tests for the five Phase 4 tables."""

from datetime import date
from uuid import uuid4

from sqlalchemy.orm import Session

from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.intelligence_repo import IntelligenceRepository
from database.repositories.portfolio_repo import PortfolioRepository
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.factors.models import (
    BaseSignal,
    FactorSnapshot,
    FamaFrenchExposure,
    NormalizationMethod,
)
from quant_engine.reliability.models import ReliabilityState
from quant_engine.risk.models import RiskState
from quant_engine.signals.models import ControlledSignal, ExplainabilityPayload
from quant_engine.volatility.models import MarketRegime


def test_create_and_retrieve_complete_intelligence_bundle(db_session: Session) -> None:
    portfolio_id = f"port-{uuid4().hex[:8]}"
    PortfolioRepository(db_session).create_portfolio(portfolio_id, "Signals", "USD")
    evaluation_id = uuid4()
    as_of_date = date(2026, 9, 16)
    EvaluationRepository(db_session).create_evaluation(
        evaluation_id,
        portfolio_id,
        as_of_date,
        EvaluationTrigger.MANUAL,
        EvaluationDecision.HOLD,
        EvaluationStatus.COMPLETED,
    )
    factor = FactorSnapshot(
        ticker="AAPL",
        as_of_date=as_of_date,
        raw_factors={"ff_alpha": 0.01},
        normalized_factors={"ff_alpha": 1.0},
        normalization_method=NormalizationMethod.Z_SCORE,
    )
    base = BaseSignal(
        ticker="AAPL",
        as_of_date=as_of_date,
        base_signal=0.25,
        contributions={"ff_alpha": 0.25},
    )
    exposure = FamaFrenchExposure(
        ticker="AAPL",
        as_of_date=as_of_date,
        alpha=0.01,
        market_beta=1.0,
        smb_beta=0.1,
        hml_beta=0.2,
        rmw_beta=0.3,
        cma_beta=0.4,
        r_squared=0.8,
        observation_count=252,
    )
    reliability = ReliabilityState(
        ticker="AAPL",
        as_of_date=as_of_date,
        base_reliability=0.8,
        volatility_adjustment=0.9,
        regime_adjustment=1.0,
        recent_performance_adjustment=1.0,
        reliability_adjustment=0.8,
        effective_reliability=0.72,
    )
    risk = RiskState(
        as_of_date=as_of_date,
        volatility_risk=0.2,
        drawdown_risk=0.3,
        correlation_risk=0.4,
        concentration_risk=0.5,
        liquidity_risk=0.1,
        composite_risk=0.3,
    )
    controlled = ControlledSignal(
        ticker="AAPL",
        as_of_date=as_of_date,
        base_signal=0.25,
        volatility_adjustment=0.9,
        reliability_adjustment=0.8,
        risk_adjustment=0.7,
        controlled_signal=0.126,
    )
    explanation = ExplainabilityPayload(
        ticker="AAPL",
        as_of_date=as_of_date,
        raw_factors=factor.raw_factors,
        normalized_factors=factor.normalized_factors,
        factor_contributions=base.contributions,
        base_signal=0.25,
        effective_reliability=0.72,
        conditional_volatility=0.02,
        volatility_ratio=1.1,
        market_stress=1.0,
        regime=MarketRegime.NORMAL,
        risk_contribution=1.0,
        volatility_adjustment=0.9,
        reliability_adjustment=0.8,
        risk_adjustment=0.7,
        controlled_signal=0.126,
    )
    repository = IntelligenceRepository(db_session)

    repository.create_bundle(
        evaluation_id,
        portfolio_id,
        factors=[factor],
        base_signals=[base],
        exposures=[exposure],
        reliabilities=[reliability],
        risk=risk,
        controlled_signals=[controlled],
        explanations=[explanation],
        risk_contributions={"AAPL": 1.0},
    )
    db_session.commit()

    assert repository.has_evaluation(evaluation_id)
    assert repository.get_factors(evaluation_id)[0].raw_factors == {"ff_alpha": 0.01}
    assert repository.get_exposures(evaluation_id)[0].market_beta == 1.0
    assert repository.get_reliabilities(evaluation_id)[0].effective_reliability == 0.72
    assert repository.get_risk(evaluation_id).composite_risk == 0.3
    assert repository.get_signals(evaluation_id)[0].explainability["regime"] == "NORMAL"
