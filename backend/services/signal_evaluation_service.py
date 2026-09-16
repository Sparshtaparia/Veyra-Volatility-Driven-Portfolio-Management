"""Phase 4-6 orchestration over persisted Phase 3 volatility evaluations."""
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

from quant_engine.optimization.models import (
    AssetOptimizationInput,
    OptimizationConstraints,
    AllocationResult
)
from quant_engine.optimization.engine import PortfolioOptimizer
from quant_engine.optimization.allocator import TargetAllocator


@dataclass(frozen=True)
class SignalDecisionEvaluationDTO:
    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    controls: list[ControlOutput]
    composite_risk: dict
    allocation_result: AllocationResult


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
        self.optimizer = PortfolioOptimizer()
        self.allocator = TargetAllocator(rebalance_threshold=0.05)

    def evaluate(self, portfolio_id: str, as_of_date: date, *, evaluation_id: UUID | None = None) -> SignalDecisionEvaluationDTO:
        volatility = self.volatility_service.evaluate(portfolio_id, as_of_date, evaluation_id=evaluation_id)
        by_ticker = {asset.ticker: asset for asset in volatility.asset_volatility}
        holdings = self.portfolio_service.repo.get_holdings(portfolio_id)
        holdings_by_ticker = {h.ticker: h.weight for h in holdings}
        
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
            
        # PHASE 6: Portfolio Optimization
        opt_inputs = []
        for control in controls:
            ticker = control.regulated_signal.base_signal.ticker
            
            # Re-compute or retrieve reliability score for optimization
            asset = by_ticker.get(ticker)
            reliability_out = self.reliability.compute_reliability(ticker, asset.forecast_volatility)
            
            opt_inputs.append(
                AssetOptimizationInput(
                    ticker=ticker,
                    current_weight=holdings_by_ticker.get(ticker, 0.0),
                    expected_signal=control.control_output,
                    volatility=control.volatility_state,
                    composite_risk_score=composite_risk_out.composite_score,
                    reliability_score=reliability_out.reliability_score
                )
            )
            
        constraints = OptimizationConstraints(min_weight=0.0, max_weight=0.4, turnover_limit=1.0)
        target_outputs = self.optimizer.optimize(opt_inputs, constraints)
        allocation_result = self.allocator.allocate(opt_inputs, target_outputs)
            
        return SignalDecisionEvaluationDTO(
            evaluation_id=volatility.evaluation_id, 
            portfolio_id=portfolio_id, 
            as_of_date=as_of_date, 
            controls=controls,
            composite_risk=composite_risk_out.model_dump(),
            allocation_result=allocation_result
        )
