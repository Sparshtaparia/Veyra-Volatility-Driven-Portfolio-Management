"""Full upload-to-feedback integration path for the final core architecture."""

from datetime import timedelta

from sqlalchemy.orm import Session

from backend.services.portfolio_control_service import PortfolioControlService
from backend.services.portfolio_upload_service import (
    PortfolioUploadService,
    UploadedHolding,
)
from backend.services.signal_evaluation_service import SignalEvaluationService
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from database.repositories.portfolio_control_repo import PortfolioControlRepository
from quant_engine.factors.fama_french import FamaFrenchEstimator
from quant_engine.feedback.models import FeedbackOutcome
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


def test_upload_evaluate_optimize_rebalance_persist_and_feedback(
    db_session: Session,
) -> None:
    bars, factors, as_of_date = integration_data()
    market_provider = IntegrationProvider(bars)
    upload = PortfolioUploadService(db_session, market_provider)
    portfolio = upload.create_portfolio(
        "End to end",
        "USD",
        [
            UploadedHolding(ticker=ticker, quantity=10.0, average_price=100.0)
            for ticker in ("AAA", "BBB", "CCC")
        ],
        as_of_date,
        "integration-test-user",
    )
    phase3 = VolatilityEvaluationService(
        db_session,
        market_provider,
        volatility_service=VolatilityService(
            engine=GJRGarchEngine(min_observations=252),
            aggregator=VolatilityAggregator(include_fallbacks_in_aggregation=True),
        ),
        regime_service=RegimeService(threshold_strategy=FixedThresholdStrategy(1.5)),
    )
    intelligence = SignalEvaluationService(
        db_session,
        market_provider,
        FrameFactorProvider(factors),
        volatility_evaluation_service=phase3,
        fama_french_estimator=FamaFrenchEstimator(window=252, minimum_observations=60),
    ).evaluate(portfolio.id, as_of_date)

    control_service = PortfolioControlService(db_session)
    control = control_service.optimize_and_rebalance(
        portfolio.id,
        intelligence.evaluation_id,
        sectors={"AAA": "TECH", "BBB": "FINANCE", "CCC": "HEALTH"},
    )
    feedback = control_service.apply_feedback(
        portfolio.id,
        intelligence.evaluation_id,
        FeedbackOutcome(
            observation_date=as_of_date + timedelta(days=30),
            portfolio_return=0.02,
            realized_volatility=0.018,
            drawdown=0.01,
            signal_accuracy=0.7,
            transaction_cost=sum(
                item.transaction_cost + item.slippage_cost for item in control.trades
            ),
        ),
    )
    repository = PortfolioControlRepository(db_session)

    assert len(control.optimization.targets) == 3
    assert repository.get_rebalance(intelligence.evaluation_id) is not None
    assert repository.latest_snapshot(portfolio.id) is not None
    assert feedback.updated_state.as_of_date > feedback.previous_state.as_of_date
    assert len(repository.feedback_history(portfolio.id)) == 1
