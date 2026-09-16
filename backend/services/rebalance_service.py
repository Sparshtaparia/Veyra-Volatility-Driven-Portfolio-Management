from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session

from backend.services.portfolio_service import PortfolioService
from backend.services.signal_evaluation_service import SignalEvaluationService
from database.models import RebalanceEventModel, TradeModel, PortfolioSnapshotModel
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

    def execute_paper_rebalance(self, portfolio_id: str, as_of_date: date):
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
        eval_result = self.signal_service.evaluate(portfolio_id, as_of_date)
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
        
        # 6. Persist Execution (Simulated)
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
        self.db.flush() # flush to get event.event_id
        
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
            
        # Save snapshot of simulated holdings
        new_total_value = sum(h["market_value"] for h in result.simulated_holdings)
        snapshot = PortfolioSnapshotModel(
            portfolio_id=portfolio_id,
            evaluation_id=result.evaluation_id,
            snapshot_date=as_of_date,
            portfolio_value=new_total_value,
            cash_value=0.0, # Simple assumption
            gross_exposure=1.0,
            net_exposure=1.0,
            holdings=result.simulated_holdings
        )
        
        # Avoid duplicate snapshot for same date if exists (for idempotency in tests/dev)
        existing_snapshot = self.db.query(PortfolioSnapshotModel).filter_by(
            portfolio_id=portfolio_id, snapshot_date=as_of_date
        ).first()
        if existing_snapshot:
            self.db.delete(existing_snapshot)
            self.db.flush()
            
        self.db.add(snapshot)
        self.db.commit()

        return result
