"""Application workflow from controlled signals to paper execution and feedback."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from database.repositories.intelligence_repo import IntelligenceRepository
from database.repositories.portfolio_control_repo import PortfolioControlRepository
from database.repositories.portfolio_repo import PortfolioRepository
from database.repositories.regime_repo import RegimeRepository
from database.repositories.volatility_repo import VolatilityRepository
from quant_engine.feedback.engine import FeedbackController
from quant_engine.feedback.models import FeedbackOutcome, FeedbackUpdate, SystemState
from quant_engine.portfolio.exposure import ExposureController
from quant_engine.portfolio.models import (
    AssetAllocationInput,
    ExecutedTrade,
    ExposureConfig,
    OptimizationResult,
    OptimizerConfig,
    TargetWeight,
)
from quant_engine.portfolio.optimizer import PortfolioOptimizer
from quant_engine.portfolio.rebalance import RebalanceEngine, SimulatedExecutor


@dataclass(frozen=True)
class PortfolioControlDTO:
    evaluation_id: UUID
    portfolio_id: str
    optimization: OptimizationResult
    trades: list[ExecutedTrade]
    rebalance_event_id: UUID


class PortfolioControlService:
    def __init__(
        self,
        db: Session,
        *,
        exposure_controller: ExposureController | None = None,
        optimizer: PortfolioOptimizer | None = None,
        rebalance_engine: RebalanceEngine | None = None,
        executor: SimulatedExecutor | None = None,
        feedback_controller: FeedbackController | None = None,
    ) -> None:
        self.db = db
        self.portfolios = PortfolioRepository(db)
        self.intelligence = IntelligenceRepository(db)
        self.volatility = VolatilityRepository(db)
        self.regimes = RegimeRepository(db)
        self.repository = PortfolioControlRepository(db)
        self.exposure_controller = exposure_controller or ExposureController()
        self.optimizer = optimizer or PortfolioOptimizer()
        self.rebalance_engine = rebalance_engine or RebalanceEngine()
        self.executor = executor or SimulatedExecutor()
        self.feedback_controller = feedback_controller or FeedbackController()

    def optimize_and_rebalance(
        self,
        portfolio_id: str,
        evaluation_id: UUID,
        *,
        sectors: dict[str, str] | None = None,
        exposure_config: ExposureConfig | None = None,
        optimizer_config: OptimizerConfig | None = None,
        transaction_cost_bps: float | None = None,
        slippage_bps: float | None = None,
    ) -> PortfolioControlDTO:
        existing = self.repository.get_rebalance(evaluation_id)
        if existing is not None:
            return self.get_portfolio_control(evaluation_id, portfolio_id)
        portfolio = self.portfolios.get_portfolio(portfolio_id)
        if portfolio is None:
            raise ValueError("portfolio not found")
        holdings = self.portfolios.get_holdings(portfolio_id)
        signals = self.intelligence.get_signals(evaluation_id)
        risk = self.intelligence.get_risk(evaluation_id)
        regime = self.regimes.get_by_evaluation(evaluation_id)
        volatility = self.volatility.get_by_evaluation(evaluation_id)
        if not signals or risk is None or regime is None or not volatility:
            raise ValueError("evaluation is missing Phase 3 or Phase 4 state")
        signal_map = {item.ticker: item for item in signals}
        volatility_map = {item.ticker: item for item in volatility}
        missing = sorted(
            holding.ticker
            for holding in holdings
            if holding.ticker not in signal_map or holding.ticker not in volatility_map
        )
        if missing:
            raise ValueError(f"evaluation is missing asset state for: {', '.join(missing)}")
        sectors = {key.upper(): value for key, value in (sectors or {}).items()}
        assets = [
            AssetAllocationInput(
                ticker=holding.ticker,
                sector=sectors.get(holding.ticker, "UNKNOWN"),
                current_weight=holding.weight,
                controlled_signal=signal_map[holding.ticker].controlled_signal,
                conditional_volatility=volatility_map[holding.ticker].conditional_volatility,
            )
            for holding in holdings
        ]
        exposure_controller = (
            ExposureController(exposure_config) if exposure_config else self.exposure_controller
        )
        optimizer = PortfolioOptimizer(optimizer_config) if optimizer_config else self.optimizer
        executor = (
            SimulatedExecutor(transaction_cost_bps, slippage_bps)
            if transaction_cost_bps is not None and slippage_bps is not None
            else self.executor
        )
        exposure = exposure_controller.calculate(regime.regime, risk.composite_risk)
        result = optimizer.optimize(regime.as_of_date, assets, exposure)
        prices = {holding.ticker: holding.current_price for holding in holdings}
        instructions = self.rebalance_engine.calculate(
            result.targets, portfolio.total_value, prices
        )
        trades = executor.execute(instructions)
        try:
            self.repository.create_targets(evaluation_id, portfolio_id, result)
            event = self.repository.create_rebalance(
                evaluation_id,
                portfolio_id,
                result.as_of_date,
                portfolio.total_value,
                result.expected_turnover,
                trades,
            )
            snapshot_holdings = [
                {
                    "ticker": target.ticker,
                    "target_weight": target.target_weight,
                    "quantity": target.target_weight
                    * portfolio.total_value
                    / prices[target.ticker],
                    "price": prices[target.ticker],
                }
                for target in result.targets
            ]
            self.repository.create_snapshot(
                portfolio_id,
                evaluation_id,
                result.as_of_date,
                portfolio.total_value,
                result.cash_weight * portfolio.total_value,
                result.gross_exposure,
                result.net_exposure,
                snapshot_holdings,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return PortfolioControlDTO(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            optimization=result,
            trades=trades,
            rebalance_event_id=event.event_id,
        )

    def apply_feedback(
        self,
        portfolio_id: str,
        evaluation_id: UUID,
        outcome: FeedbackOutcome,
    ) -> FeedbackUpdate:
        risk = self.intelligence.get_risk(evaluation_id)
        regime = self.regimes.get_by_evaluation(evaluation_id)
        signals = self.intelligence.get_signals(evaluation_id)
        snapshot = self.repository.latest_snapshot(portfolio_id)
        if risk is None or regime is None or not signals or snapshot is None:
            raise ValueError("feedback requires completed portfolio-control state")
        history = self.repository.feedback_history(portfolio_id)
        if history:
            previous = SystemState.model_validate(history[-1].updated_state)
        else:
            previous = SystemState(
                as_of_date=regime.as_of_date,
                volatility_distribution_level=max(regime.aggregate_volatility, 1e-12),
                adaptive_threshold=max(regime.adaptive_threshold, 1e-12),
                reliability_multiplier=1.0,
                risk_limit=max(0.01, 1.0 - risk.composite_risk),
                exposure_limit=snapshot.gross_exposure,
                portfolio_value=snapshot.portfolio_value,
            )
        aggregate_signal = sum(item.controlled_signal for item in signals) / len(signals)
        update = self.feedback_controller.update(previous, aggregate_signal, outcome)
        try:
            self.repository.create_feedback(evaluation_id, portfolio_id, update)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return update

    def get_portfolio_control(self, evaluation_id: UUID, portfolio_id: str) -> PortfolioControlDTO:
        targets = self.repository.get_targets(evaluation_id)
        event = self.repository.get_rebalance(evaluation_id)
        if not targets or event is None:
            raise ValueError("portfolio control result not found")
        trades = [
            ExecutedTrade.model_validate(item, from_attributes=True)
            for item in self.repository.get_trades(event.event_id)
        ]
        result = OptimizationResult(
            as_of_date=targets[0].as_of_date,
            targets=[
                TargetWeight(
                    ticker=item.ticker,
                    sector=item.sector,
                    current_weight=item.current_weight,
                    inverse_volatility_weight=item.inverse_volatility_weight,
                    target_weight=item.target_weight,
                    weight_change=item.weight_change,
                )
                for item in targets
            ],
            gross_exposure=targets[0].gross_exposure,
            net_exposure=targets[0].net_exposure,
            cash_weight=targets[0].cash_weight,
            expected_volatility=targets[0].expected_volatility,
            expected_turnover=event.turnover,
            solver_status="persisted",
        )
        return PortfolioControlDTO(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            optimization=result,
            trades=trades,
            rebalance_event_id=event.event_id,
        )
