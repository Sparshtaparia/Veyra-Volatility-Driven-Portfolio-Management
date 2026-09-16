"""Full Phase 4 application integration path with deterministic providers."""

from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.services.signal_evaluation_service import SignalEvaluationService
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from database.repositories.intelligence_repo import IntelligenceRepository
from database.repositories.portfolio_repo import PortfolioRepository
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MarketDataProvider
from quant_engine.factors.fama_french import FACTOR_COLUMNS, FamaFrenchEstimator
from quant_engine.factors.provider import FactorDataProvider
from quant_engine.regimes.service import RegimeService
from quant_engine.regimes.threshold import FixedThresholdStrategy
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.gjr_garch import GJRGarchEngine
from quant_engine.volatility.service import VolatilityService


class IntegrationProvider(MarketDataProvider):
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars

    def get_history(self, ticker: str, start_date: date, end_date: date):
        return [
            bar
            for bar in self.bars
            if bar.ticker == ticker and start_date <= bar.timestamp <= end_date
        ]


class FrameFactorProvider(FactorDataProvider):
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def get_history(self, start_date: date, end_date: date) -> pd.DataFrame:
        return self.frame.loc[str(start_date) : str(end_date)]


def integration_data():
    index = pd.date_range("2025-01-01", periods=320, freq="D")
    generator = np.random.default_rng(42)
    factors = pd.DataFrame(
        generator.normal(0.0, 0.006, (len(index), 5)),
        index=index,
        columns=FACTOR_COLUMNS,
    )
    factors["RF"] = 0.0001
    bars = []
    coefficients = {
        "AAA": np.array([1.0, 0.2, 0.1, 0.1, -0.1]),
        "BBB": np.array([0.8, -0.1, 0.3, 0.2, 0.1]),
        "CCC": np.array([1.2, 0.1, -0.2, 0.4, 0.2]),
    }
    for ticker, beta in coefficients.items():
        returns = 0.0002 + factors[list(FACTOR_COLUMNS)].to_numpy() @ beta
        prices = 100.0 * np.exp(np.cumsum(returns))
        for timestamp, close in zip(index, prices, strict=True):
            bars.append(
                MarketBar(
                    ticker=ticker,
                    timestamp=timestamp.date(),
                    open=float(close * 0.999),
                    high=float(close * 1.01),
                    low=float(close * 0.99),
                    close=float(close),
                    volume=1_000_000.0 + len(bars),
                )
            )
    return bars, factors, index[-1].date()


def test_full_market_to_controlled_signal_path(db_session: Session) -> None:
    bars, factors, as_of_date = integration_data()
    market_provider = IntegrationProvider(bars)
    portfolio_id = "port-phase4"
    portfolio_repository = PortfolioRepository(db_session)
    portfolio_repository.create_portfolio(portfolio_id, "Phase 4", "USD")
    for ticker in ("AAA", "BBB", "CCC"):
        portfolio_repository.add_holding(portfolio_id, ticker, 1.0, 100.0, 100.0, 100.0, 1.0 / 3.0)
    phase3 = VolatilityEvaluationService(
        db_session,
        market_provider,
        volatility_service=VolatilityService(
            engine=GJRGarchEngine(min_observations=252),
            aggregator=VolatilityAggregator(include_fallbacks_in_aggregation=True),
        ),
        regime_service=RegimeService(threshold_strategy=FixedThresholdStrategy(1.5)),
    )
    service = SignalEvaluationService(
        db_session,
        market_provider,
        FrameFactorProvider(factors),
        volatility_evaluation_service=phase3,
        fama_french_estimator=FamaFrenchEstimator(window=252, minimum_observations=60),
    )

    result = service.evaluate(portfolio_id, as_of_date)

    assert len(result.controlled_signals) == 3
    assert len(result.explainability) == 3
    assert 0.0 <= result.risk_state.composite_risk <= 1.0
    assert all(item.raw_factors["ff_alpha"] is not None for item in result.explainability)
    repository = IntelligenceRepository(db_session)
    assert len(repository.get_factors(result.evaluation_id)) == 3
    assert len(repository.get_exposures(result.evaluation_id)) == 3
    assert len(repository.get_reliabilities(result.evaluation_id)) == 3
    assert len(repository.get_signals(result.evaluation_id)) == 3

    repeated = service.evaluate(portfolio_id, as_of_date, evaluation_id=result.evaluation_id)
    assert repeated == result
