from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session

from backend.services.portfolio_service import PortfolioService
from backend.services.signal_decision_evaluation_service import SignalEvaluationService
from database.models import RebalanceEventModel, TradeModel, PortfolioSnapshotModel, VolatilityStateModel
from quant_engine.data.provider import MarketDataProvider
from quant_engine.rebalance.service import RebalancePlanner
from execution.paper.executor import PaperExecutor


class RebalanceService:
    def __init__(self, db: Session, provider: MarketDataProvider):
        self.db = db
        self.provider = provider
        self.portfolio_service = PortfolioService(db)
        self.signal_service = SignalEvaluationService(db, provider)
        self.planner = RebalancePlanner()
        self.executor = PaperExecutor()

    def execute_paper_rebalance(
        self,
        portfolio_id: str,
        as_of_date: date,
        *,
        evaluation_result=None,
    ):
        # 1. Fetch current portfolio
        portfolio = self.portfolio_service.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")

        holdings = self.portfolio_service.repo.get_holdings(portfolio_id)
        current_holdings = [
            {
                "ticker": h.ticker,
                "quantity": h.quantity,
                "average_price": h.average_price,
                "current_price": h.current_price,
                "market_value": h.market_value,
                "weight": h.weight
            } for h in holdings
        ]

        # 2. Run Phase 1-6 Pipeline to get target allocation
        eval_result = evaluation_result or self.signal_service.evaluate(portfolio_id, as_of_date)
        allocation = eval_result.allocation_result

        if allocation.decision == "HOLD":
            raise ValueError("Cannot execute rebalance: Decision is HOLD")

        # 3. Get current prices for execution
        prices = {}
        for h in holdings:
            prices[h.ticker] = self.provider.get_latest_price(h.ticker, as_of_date)

        # Add prices for any new targets that are not in current holdings
        for alloc in allocation.allocations:
            if alloc.ticker not in prices:
                prices[alloc.ticker] = self.provider.get_latest_price(alloc.ticker, as_of_date)

        # 4. Generate Rebalance Plan (Phase 7a)
        plan = self.planner.generate_plan(
            evaluation_id=eval_result.evaluation_id,
            portfolio_id=portfolio_id,
            allocation=allocation,
            current_prices=prices,
            portfolio_value=portfolio.total_value
        )

        # 5. Execute Paper Trades (Phase 7b)
        result = self.executor.execute(plan, current_holdings)

        # 6. Persist Execution (Simulated) — real HoldingModel rows are NOT touched
        event = RebalanceEventModel(
            evaluation_id=result.evaluation_id,
            portfolio_id=result.portfolio_id,
            event_date=as_of_date,
            status="COMPLETED",
            portfolio_value=portfolio.total_value,
            turnover=plan.total_turnover,
            total_cost=result.total_cost
        )
        self.db.add(event)
        self.db.flush()  # flush to get event.event_id

        for order in result.orders:
            trade = TradeModel(
                event_id=event.event_id,
                ticker=order.ticker,
                side=order.side,
                quantity=order.quantity,
                reference_price=order.reference_price,
                execution_price=order.execution_price,
                gross_notional=order.gross_notional,
                transaction_cost=order.transaction_cost,
                slippage_cost=order.slippage_cost,
                net_cash_change=order.net_cash_change,
            )
            self.db.add(trade)

        # Simulated portfolio snapshot — separate from live holdings
        new_total_value = sum(h["market_value"] for h in result.simulated_holdings)
        snapshot = PortfolioSnapshotModel(
            portfolio_id=portfolio_id,
            evaluation_id=result.evaluation_id,
            snapshot_date=as_of_date,
            portfolio_value=new_total_value,
            cash_value=0.0,
            gross_exposure=1.0,
            net_exposure=1.0,
            holdings=result.simulated_holdings
        )

        # Idempotency: remove existing snapshot for same date before inserting
        existing_snapshot = self.db.query(PortfolioSnapshotModel).filter_by(
            portfolio_id=portfolio_id, snapshot_date=as_of_date
        ).first()
        if existing_snapshot:
            self.db.delete(existing_snapshot)
            self.db.flush()

        self.db.add(snapshot)

        # 7. Phase 8: Feedback & Adaptive Threshold
        # Timing contract:
        #   t0: Evaluation runs, Phase 3 computes adaptive_threshold T0 from historical stress data.
        #   t1: Paper rebalance completes (this point in the code).
        #   t1: We observe portfolio volatility from the Phase 3 conditional estimates.
        #       These are computed from PAST returns only (no lookahead).
        #   t1: Compute feedback error and T1.
        #   T1 is persisted here and read by the NEXT evaluation's regime service.
        from quant_engine.feedback.service import FeedbackService
        from database.models import FeedbackUpdateModel, RegimeStateModel

        feedback_service = FeedbackService()

        # Source of previous_threshold (priority order):
        #   1. Most recent FeedbackUpdateModel.updated_state.adaptive_threshold  (Phase 8 chain)
        #   2. Most recent RegimeStateModel.adaptive_threshold                   (Phase 3 baseline)
        #   3. Hard default 0.05
        latest_feedback = (
            self.db.query(FeedbackUpdateModel)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(FeedbackUpdateModel.observation_date.desc())
            .first()
        )
        latest_regime = (
            self.db.query(RegimeStateModel)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(RegimeStateModel.as_of_date.desc())
            .first()
        )

        if latest_feedback:
            prev_threshold = float(latest_feedback.updated_state.get("adaptive_threshold", 0.05))
        elif latest_regime:
            prev_threshold = latest_regime.adaptive_threshold
        else:
            prev_threshold = 0.05

        # Observed volatility: portfolio-weighted average of per-asset conditional_volatility.
        # These are Phase 3 GJR-GARCH estimates computed from historical returns — no future data.
        # We apply the new simulated portfolio weights to get the expected portfolio-level volatility
        # after rebalancing.
        vol_states = (
            self.db.query(VolatilityStateModel)
            .filter_by(evaluation_id=eval_result.evaluation_id)
            .all()
        )
        vol_map = {vs.ticker: vs.conditional_volatility for vs in vol_states}
        observed_vol = sum(
            h["weight"] * vol_map.get(h["ticker"], 0.02)
            for h in result.simulated_holdings
        )

        feedback = feedback_service.calculate_feedback(
            evaluation_id=result.evaluation_id,
            portfolio_id=portfolio_id,
            previous_threshold=prev_threshold,
            observed_volatility=observed_vol,
            observation_date=as_of_date,
        )

        feedback_model = FeedbackUpdateModel(
            evaluation_id=feedback.evaluation_id,
            portfolio_id=portfolio_id,
            observation_date=as_of_date,
            previous_state={"adaptive_threshold": feedback.previous_threshold},
            controlled_signal=0.0,  # Required by schema; semantic: no single signal for the portfolio-level update
            observed_outcome={
                "observed_volatility": feedback.observed_volatility,
                "feedback_error": feedback.feedback_error,
            },
            updated_state={"adaptive_threshold": feedback.updated_threshold},
        )

        # Idempotency: replace existing feedback for same portfolio+date
        existing_feedback = (
            self.db.query(FeedbackUpdateModel)
            .filter_by(portfolio_id=portfolio_id, observation_date=as_of_date)
            .first()
        )
        if existing_feedback:
            self.db.delete(existing_feedback)
            self.db.flush()

        self.db.add(feedback_model)
        self.db.commit()

        return result
