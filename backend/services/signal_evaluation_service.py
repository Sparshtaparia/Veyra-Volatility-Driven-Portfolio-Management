<<<<<<< HEAD
"""Phase 4 orchestration over persisted Phase 3 volatility evaluations."""
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from backend.services.portfolio_service import PortfolioService
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from quant_engine.control.models import ControlOutput
from quant_engine.control.service import StateCoupledControl
from quant_engine.data.provider import MarketDataProvider
from quant_engine.features.service import FeatureService
from quant_engine.signal_control.service import SignalRegulator
from quant_engine.signals.service import SignalService

from quant_engine.reliability.service import ReliabilityService
from quant_engine.risk.service import CompositeRiskService

@dataclass(frozen=True)
class SignalDecisionEvaluationDTO:
    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    controls: list[ControlOutput]
    composite_risk: dict


class SignalEvaluationService:
    def __init__(self, db: Session, provider: MarketDataProvider, *, volatility_service: VolatilityEvaluationService | None = None) -> None:
        self.portfolio_service = PortfolioService(db)
        self.provider = provider
        self.volatility_service = volatility_service or VolatilityEvaluationService(db, provider)
        self.features = FeatureService(provider)
        self.signals = SignalService()
        self.regulator = SignalRegulator()
        self.reliability = ReliabilityService()
        self.risk = CompositeRiskService()
        self.control = StateCoupledControl()

    def evaluate(self, portfolio_id: str, as_of_date: date, *, evaluation_id: UUID | None = None) -> SignalDecisionEvaluationDTO:
        volatility = self.volatility_service.evaluate(portfolio_id, as_of_date, evaluation_id=evaluation_id)
        by_ticker = {asset.ticker: asset for asset in volatility.asset_volatility}
        holdings = self.portfolio_service.repo.get_holdings(portfolio_id)
        
        # Calculate Phase 5 Composite Risk at portfolio level
        holdings_dicts = [{"ticker": h.ticker, "weight": h.weight} for h in holdings]
        asset_vols = {a.ticker: a.forecast_volatility for a in volatility.asset_volatility}
        composite_risk_out = self.risk.compute_risk(portfolio_id, holdings_dicts, asset_vols)
        
        controls: list[ControlOutput] = []
        for holding in holdings:
            snapshots = self.features.generate_features(holding.ticker, as_of_date - timedelta(days=120), as_of_date)
            usable = [snapshot for snapshot in snapshots if snapshot.timestamp <= as_of_date and None not in (snapshot.rsi, snapshot.macd_histogram, snapshot.atr, snapshot.bollinger_band_width)]
            if not usable:
                raise ValueError(f"Insufficient feature history for {holding.ticker}")
            asset = by_ticker.get(holding.ticker.strip().upper())
            if asset is None:
                raise ValueError(f"No volatility state available for {holding.ticker}")
            
            base = self.signals.generate(usable[-1])
            regulated = self.regulator.regulate(base, regime=volatility.market_regime.regime, volatility_ratio=asset.volatility_ratio)
            
            # Calculate Phase 5 Reliability at asset level
            reliability_out = self.reliability.compute_reliability(holding.ticker, asset.forecast_volatility)
            
            controls.append(self.control.apply(
                regulated, 
                volatility_state=asset.forecast_volatility, 
                risk_state=composite_risk_out.risk_state, 
                reliability_state=reliability_out.reliability_state
            ))
            
        return SignalDecisionEvaluationDTO(
            evaluation_id=volatility.evaluation_id, 
            portfolio_id=portfolio_id, 
            as_of_date=as_of_date, 
            controls=controls,
            composite_risk=composite_risk_out.model_dump()
        )
=======
"""Application orchestration for the Phase 4 intelligence pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.exceptions import SignalEvaluationNotFoundError, SignalPersistenceError
from backend.services.portfolio_service import PortfolioService
from backend.services.volatility_evaluation_service import (
    VolatilityEvaluationDTO,
    VolatilityEvaluationService,
)
from database.repositories.intelligence_repo import IntelligenceRepository
from quant_engine.data.provider import MarketDataProvider
from quant_engine.data.returns import calculate_log_returns
from quant_engine.factors.fama_french import FamaFrenchEstimator
from quant_engine.factors.models import (
    BaseSignal,
    FactorSnapshot,
    FamaFrenchExposure,
    NormalizationMethod,
)
from quant_engine.factors.normalization import normalize_cross_section
from quant_engine.factors.provider import FactorDataProvider
from quant_engine.factors.signal import BaseSignalEngine
from quant_engine.features.service import FeatureService
from quant_engine.reliability.engine import ReliabilityEngine
from quant_engine.reliability.models import ReliabilityState
from quant_engine.risk.engine import RiskStateEngine
from quant_engine.risk.models import RiskState
from quant_engine.signals.models import ControlledSignal, ExplainabilityPayload
from quant_engine.signals.operator import StateCoupledOperator


@dataclass(frozen=True)
class SignalEvaluationDTO:
    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    risk_state: RiskState
    controlled_signals: list[ControlledSignal]
    explainability: list[ExplainabilityPayload]


class _AsOfProvider(MarketDataProvider):
    def __init__(self, provider: MarketDataProvider, as_of_date: date) -> None:
        self.provider = provider
        self.as_of_date = as_of_date

    def get_history(self, ticker: str, start_date: date, end_date: date):
        return [
            bar
            for bar in self.provider.get_history(ticker, start_date, end_date)
            if bar.timestamp <= self.as_of_date
        ]


class SignalEvaluationService:
    def __init__(
        self,
        db: Session,
        market_data_provider: MarketDataProvider,
        factor_data_provider: FactorDataProvider,
        *,
        volatility_evaluation_service: VolatilityEvaluationService | None = None,
        fama_french_estimator: FamaFrenchEstimator | None = None,
        base_signal_engine: BaseSignalEngine | None = None,
        reliability_engine: ReliabilityEngine | None = None,
        risk_engine: RiskStateEngine | None = None,
        operator: StateCoupledOperator | None = None,
        normalization_method: NormalizationMethod = NormalizationMethod.Z_SCORE,
        lookback_days: int = 550,
    ) -> None:
        self.db = db
        self.market_data_provider = market_data_provider
        self.factor_data_provider = factor_data_provider
        self.volatility_service = volatility_evaluation_service or VolatilityEvaluationService(
            db, market_data_provider
        )
        self.ff_estimator = fama_french_estimator or FamaFrenchEstimator()
        self.base_signal_engine = base_signal_engine or BaseSignalEngine()
        self.reliability_engine = reliability_engine or ReliabilityEngine()
        self.risk_engine = risk_engine or RiskStateEngine()
        self.operator = operator or StateCoupledOperator()
        self.normalization_method = normalization_method
        self.lookback_days = lookback_days
        self.portfolio_service = PortfolioService(db)
        self.repository = IntelligenceRepository(db)

    def evaluate(
        self,
        portfolio_id: str,
        as_of_date: date,
        *,
        evaluation_id: UUID | None = None,
    ) -> SignalEvaluationDTO:
        portfolio = self.portfolio_service.get_portfolio(portfolio_id)
        holdings = self.portfolio_service.repo.get_holdings(portfolio_id)
        volatility = self.volatility_service.evaluate(
            portfolio_id, as_of_date, evaluation_id=evaluation_id
        )
        if self.repository.has_evaluation(volatility.evaluation_id):
            return self.get_evaluation(volatility.evaluation_id)

        start_date = as_of_date - timedelta(days=self.lookback_days)
        factor_returns = self.factor_data_provider.get_history(start_date, as_of_date)
        bounded_provider = _AsOfProvider(self.market_data_provider, as_of_date)
        feature_service = FeatureService(bounded_provider)
        returns: dict[str, pd.Series] = {}
        raw_factors: dict[str, dict[str, float]] = {}
        exposures: list[FamaFrenchExposure] = []
        dollar_volume: dict[str, float] = {}
        volatility_by_ticker = {item.ticker: item for item in volatility.asset_volatility}

        for holding in holdings:
            bars = bounded_provider.get_history(
                holding.ticker, start_date, as_of_date + timedelta(days=1)
            )
            asset_returns = calculate_log_returns(bars)
            returns[holding.ticker] = asset_returns
            snapshots = feature_service.generate_features(
                holding.ticker, start_date, as_of_date + timedelta(days=1)
            )
            current = next(
                (item for item in reversed(snapshots) if item.timestamp <= as_of_date), None
            )
            if current is None:
                raise ValueError(f"No feature snapshot available for {holding.ticker}")
            exposure = self.ff_estimator.estimate(
                holding.ticker, asset_returns, factor_returns, as_of_date
            )
            exposures.append(exposure)
            asset_volatility = volatility_by_ticker[holding.ticker]
            values = {
                "rsi": self._required(current.rsi, "rsi", holding.ticker),
                "atr": self._required(current.atr, "atr", holding.ticker),
                "macd_histogram": self._required(
                    current.macd_histogram, "macd_histogram", holding.ticker
                ),
                "bollinger_band_width": self._required(
                    current.bollinger_band_width, "bollinger_band_width", holding.ticker
                ),
                "dollar_volume": self._required(
                    current.dollar_volume, "dollar_volume", holding.ticker
                ),
                "ff_alpha": exposure.alpha,
                "market_beta": exposure.market_beta,
                "smb_beta": exposure.smb_beta,
                "hml_beta": exposure.hml_beta,
                "rmw_beta": exposure.rmw_beta,
                "cma_beta": exposure.cma_beta,
                "conditional_volatility": asset_volatility.conditional_volatility,
                "volatility_ratio": asset_volatility.volatility_ratio,
            }
            raw_factors[holding.ticker] = values
            dollar_volume[holding.ticker] = values["dollar_volume"]

        normalized = normalize_cross_section(raw_factors, self.normalization_method)
        factor_states = [
            FactorSnapshot(
                ticker=ticker,
                as_of_date=as_of_date,
                raw_factors=values,
                normalized_factors=normalized[ticker],
                normalization_method=self.normalization_method,
            )
            for ticker, values in raw_factors.items()
        ]
        base_signals = [self.base_signal_engine.calculate(item) for item in factor_states]
        weights = {holding.ticker: holding.weight for holding in holdings}
        conditional_volatility = {
            ticker: item.conditional_volatility for ticker, item in volatility_by_ticker.items()
        }
        risk = self.risk_engine.calculate(
            as_of_date,
            weights=weights,
            conditional_volatility=conditional_volatility,
            return_history=returns,
            dollar_volume=dollar_volume,
        )
        exposure_by_ticker = {item.ticker: item for item in exposures}
        reliabilities = [
            self.reliability_engine.calculate(
                item.ticker,
                as_of_date,
                r_squared=exposure_by_ticker[item.ticker].r_squared,
                volatility_ratio=volatility_by_ticker[item.ticker].volatility_ratio,
                regime=volatility.market_regime.regime,
                recent_performance_score=self._recent_performance_score(
                    portfolio_id, item.ticker, as_of_date, returns[item.ticker]
                ),
            )
            for item in base_signals
        ]
        reliability_by_ticker = {item.ticker: item for item in reliabilities}
        controlled = [
            self.operator.apply(
                item.ticker,
                as_of_date,
                base_signal=item.base_signal,
                volatility_adjustment=reliability_by_ticker[item.ticker].volatility_adjustment,
                reliability_adjustment=reliability_by_ticker[item.ticker].reliability_adjustment,
                composite_risk=risk.composite_risk,
            )
            for item in base_signals
        ]
        risk_contributions = self._risk_contributions(weights, conditional_volatility)
        explanations = self._explanations(
            factor_states,
            base_signals,
            reliabilities,
            controlled,
            volatility,
            risk_contributions,
        )
        try:
            self.repository.create_bundle(
                volatility.evaluation_id,
                portfolio.id,
                factors=factor_states,
                base_signals=base_signals,
                exposures=exposures,
                reliabilities=reliabilities,
                risk=risk,
                controlled_signals=controlled,
                explanations=explanations,
                risk_contributions=risk_contributions,
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if self.repository.has_evaluation(volatility.evaluation_id):
                return self.get_evaluation(volatility.evaluation_id)
            raise
        except Exception as exc:
            self.db.rollback()
            raise SignalPersistenceError("Could not persist signal evaluation") from exc
        return self.get_evaluation(volatility.evaluation_id)

    def get_evaluation(self, evaluation_id: UUID) -> SignalEvaluationDTO:
        risk_record = self.repository.get_risk(evaluation_id)
        signal_records = self.repository.get_signals(evaluation_id)
        if risk_record is None or not signal_records:
            raise SignalEvaluationNotFoundError(str(evaluation_id))
        risk = RiskState.model_validate(risk_record, from_attributes=True)
        controlled = [
            ControlledSignal.model_validate(item, from_attributes=True) for item in signal_records
        ]
        explanations = [
            ExplainabilityPayload.model_validate(item.explainability) for item in signal_records
        ]
        return SignalEvaluationDTO(
            evaluation_id=evaluation_id,
            portfolio_id=risk_record.portfolio_id,
            as_of_date=risk.as_of_date,
            risk_state=risk,
            controlled_signals=controlled,
            explainability=explanations,
        )

    def get_risk(self, evaluation_id: UUID) -> RiskState:
        return self.get_evaluation(evaluation_id).risk_state

    def get_explainability(self, evaluation_id: UUID) -> list[ExplainabilityPayload]:
        return self.get_evaluation(evaluation_id).explainability

    @staticmethod
    def _required(value: float | None, name: str, ticker: str) -> float:
        if value is None:
            raise ValueError(f"Feature {name} is unavailable for {ticker}")
        return value

    @staticmethod
    def _risk_contributions(
        weights: dict[str, float], volatility: dict[str, float]
    ) -> dict[str, float]:
        amounts = {ticker: weights[ticker] * volatility[ticker] for ticker in weights}
        total = sum(amounts.values())
        return {ticker: value / total if total else 0.0 for ticker, value in amounts.items()}

    def _recent_performance_score(
        self,
        portfolio_id: str,
        ticker: str,
        as_of_date: date,
        returns: pd.Series,
    ) -> float:
        history = self.repository.get_signal_history(portfolio_id, ticker, as_of_date)
        outcomes = []
        for signal in history:
            future = returns.loc[returns.index > pd.Timestamp(signal.as_of_date)]
            if future.empty or signal.controlled_signal == 0.0:
                continue
            outcomes.append(
                1.0 if np.sign(signal.controlled_signal) == np.sign(float(future.iloc[0])) else -1.0
            )
        return float(np.mean(outcomes)) if outcomes else 0.0

    @staticmethod
    def _explanations(
        factors: list[FactorSnapshot],
        bases: list[BaseSignal],
        reliabilities: list[ReliabilityState],
        controlled: list[ControlledSignal],
        volatility: VolatilityEvaluationDTO,
        risk_contributions: dict[str, float],
    ) -> list[ExplainabilityPayload]:
        base_map = {item.ticker: item for item in bases}
        reliability_map = {item.ticker: item for item in reliabilities}
        controlled_map = {item.ticker: item for item in controlled}
        volatility_map = {item.ticker: item for item in volatility.asset_volatility}
        output = []
        for factor in factors:
            base = base_map[factor.ticker]
            reliability = reliability_map[factor.ticker]
            signal = controlled_map[factor.ticker]
            vol = volatility_map[factor.ticker]
            output.append(
                ExplainabilityPayload(
                    ticker=factor.ticker,
                    as_of_date=factor.as_of_date,
                    raw_factors=factor.raw_factors,
                    normalized_factors=factor.normalized_factors,
                    factor_contributions=base.contributions,
                    base_signal=base.base_signal,
                    effective_reliability=reliability.effective_reliability,
                    conditional_volatility=vol.conditional_volatility,
                    volatility_ratio=vol.volatility_ratio,
                    market_stress=volatility.market_regime.stress_score,
                    regime=volatility.market_regime.regime,
                    risk_contribution=risk_contributions[factor.ticker],
                    volatility_adjustment=signal.volatility_adjustment,
                    reliability_adjustment=signal.reliability_adjustment,
                    risk_adjustment=signal.risk_adjustment,
                    controlled_signal=signal.controlled_signal,
                )
            )
        return output
>>>>>>> origin/main
