"""
Chronological pipeline backtesting engine.
Simulates the full Veyra Phase 1-8 pipeline over historical data.
"""

from datetime import date
from math import sqrt
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.services.portfolio_service import PortfolioService
from backend.services.rebalance_service import RebalanceService
from backend.services.signal_evaluation_service import SignalEvaluationService
from database.models import Base, PortfolioSnapshotModel, FeedbackUpdateModel
from quant_engine.backtest.models import (
    BacktestMetrics,
    PipelineBacktestConfig,
    PipelineBacktestResult,
    PipelineEvaluationRecord,
)
from quant_engine.data.provider import MarketDataProvider
from quant_engine.data.returns import calculate_log_returns


class PipelineBacktester:
    """
    Executes a chronological, lookahead-safe simulation of the complete Veyra pipeline.
    Uses an isolated in-memory database to reuse production services exactly as they run live.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        config: PipelineBacktestConfig,
    ) -> None:
        self.provider = provider
        self.config = config

    def run(self, name: str, benchmark_returns: pd.Series) -> PipelineBacktestResult:
        # Create an isolated in-memory DB for the backtest
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            return self._execute_simulation(name, benchmark_returns, db)
        finally:
            db.close()
            Base.metadata.drop_all(engine)

    def _execute_simulation(
        self, name: str, benchmark_returns: pd.Series, db
    ) -> PipelineBacktestResult:
        # 1. Setup Portfolio
        portfolio_id = str(uuid4())
        portfolio_service = PortfolioService(db)
        portfolio = portfolio_service.repo.create_portfolio(
            portfolio_id=portfolio_id,
            user_id="backtest_user",
            name="Backtest Portfolio",
            currency="USD",
        )
        
        # Initial cash allocation
        portfolio_service.repo.add_holding(
            portfolio_id=portfolio_id,
            ticker="CASH",
            quantity=100000.0,
            average_price=1.0,
            current_price=1.0,
            market_value=100000.0,
            weight=1.0
        )

        signal_service = SignalEvaluationService(db, self.provider)
        rebalance_service = RebalanceService(db, self.provider)
        
        # Override planner thresholds
        rebalance_service.planner.rebalance_threshold = self.config.rebalance_threshold

        # Generate evaluation dates (e.g. monthly, end of month)
        # Using business month end
        eval_dates = pd.date_range(
            start=self.config.start_date,
            end=self.config.end_date,
            freq="BME"
        ).date.tolist()

        records: list[PipelineEvaluationRecord] = []
        
        # Pre-load all available prices for the universe for daily valuation
        all_bars = {}
        for ticker in self.config.universe:
            all_bars[ticker] = self.provider.get_history(
                ticker, 
                self.config.start_date - pd.Timedelta(days=10), 
                self.config.end_date
            )
            
        def get_price(t: str, d: date) -> float:
            if t == "CASH":
                return 1.0
            bars = [b for b in all_bars.get(t, []) if b.timestamp <= d]
            return bars[-1].close if bars else 1.0

        current_holdings = {"CASH": 100000.0}
        portfolio_value_series = {}
        turnovers = []
        
        for eval_date in eval_dates:
            try:
                # Synchronize real holding state in DB with simulated holdings
                _sync_holdings(db, portfolio_id, current_holdings, eval_date, get_price)
                
                start_val = sum(qty * get_price(t, eval_date) for t, qty in current_holdings.items())

                # Phase 1-6: Evaluate
                # Ensure the optimizer uses only the config universe
                signal_service.optimizer.universe = self.config.universe
                
                # We skip evaluation if history is insufficient, will raise ValueError/InsufficientCoverageError
                eval_result = signal_service.evaluate(portfolio_id, eval_date)
                
                rebalance_executed = False
                turnover = 0.0
                transaction_cost = 0.0
                
                if eval_result.allocation_result.decision != "HOLD":
                    # Phase 7 & 8: Rebalance and Feedback
                    rebalance_result = rebalance_service.execute_paper_rebalance(portfolio_id, eval_date)
                    
                    # Apply slippage & transaction costs (override default paper execution costs)
                    turnover = rebalance_result.plan.total_turnover
                    transaction_cost = (
                        start_val 
                        * turnover 
                        * (self.config.transaction_cost_bps + self.config.slippage_bps) 
                        / 10000.0
                    )
                    
                    # Update our local tracking holdings from the simulated result
                    current_holdings = {
                        h["ticker"]: h["quantity"] 
                        for h in rebalance_result.simulated_holdings
                    }
                    
                    # Deduct transaction cost from CASH
                    if "CASH" in current_holdings:
                        current_holdings["CASH"] -= transaction_cost
                    else:
                        current_holdings["CASH"] = -transaction_cost
                        
                    rebalance_executed = True
                
                # Fetch the threshold that was just updated by Phase 8
                latest_feedback = (
                    db.query(FeedbackUpdateModel)
                    .filter_by(portfolio_id=portfolio_id)
                    .order_by(FeedbackUpdateModel.observation_date.desc())
                    .first()
                )
                current_threshold = latest_feedback.updated_state.get("adaptive_threshold", 0.05) if latest_feedback else 0.05
                
                # Track daily values until next evaluation
                portfolio_value_series[eval_date] = sum(
                    qty * get_price(t, eval_date) for t, qty in current_holdings.items()
                )
                
                records.append(
                    PipelineEvaluationRecord(
                        evaluation_date=eval_date,
                        portfolio_value=portfolio_value_series[eval_date],
                        gross_return=0.0, # Computed later
                        net_return=0.0,
                        benchmark_return=0.0,
                        turnover=turnover,
                        transaction_cost=transaction_cost,
                        adaptive_threshold=current_threshold,
                        rebalance_executed=rebalance_executed,
                    )
                )
                if rebalance_executed:
                    turnovers.append(turnover)
                    
            except Exception as e:
                print(f"Eval {eval_date} skipped: {e}")
                # If evaluation fails (e.g., lack of history), just hold the current portfolio
                portfolio_value_series[eval_date] = sum(
                    qty * get_price(t, eval_date) for t, qty in current_holdings.items()
                )

        if not records:
            raise ValueError("Backtest produced no valid evaluation records")

        # Compute period returns
        values = pd.Series(portfolio_value_series).sort_index()
        net_returns = values.pct_change().dropna()
        
        benchmark = benchmark_returns.reindex(net_returns.index).fillna(0.0)
        
        # Populate returns in records
        for i, record in enumerate(records):
            if i == 0:
                continue
            r_date = record.evaluation_date
            if r_date in net_returns:
                record.net_return = float(net_returns[r_date])
                record.gross_return = record.net_return + (record.transaction_cost / values.iloc[i-1])
                record.benchmark_return = float(benchmark[r_date])
        
        metrics = self._compute_metrics(net_returns, benchmark, sum(turnovers))
        bench_metrics = self._compute_metrics(benchmark, benchmark, 0.0)

        return PipelineBacktestResult(
            name=name,
            config=self.config,
            records=records,
            metrics=metrics,
            benchmark_metrics=bench_metrics,
            evaluations_count=len(records),
            rebalances_count=sum(1 for r in records if r.rebalance_executed),
        )

    def _compute_metrics(
        self, returns: pd.Series, benchmark: pd.Series, total_turnover: float
    ) -> BacktestMetrics:
        if returns.empty:
            return BacktestMetrics(total_return=0, cagr=0, sharpe=0, sortino=0, calmar=0, max_drawdown=0, volatility=0, win_rate=0, turnover=0, alpha=0, beta=0)
            
        wealth = (1.0 + returns).cumprod()
        total_return = float(wealth.iloc[-1] - 1.0)
        years = len(returns) / 12.0  # Monthly frequency
        cagr = float(wealth.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
        
        volatility = float(returns.std(ddof=0) * sqrt(12))
        sharpe = float(returns.mean() / returns.std(ddof=0) * sqrt(12)) if returns.std(ddof=0) > 0 else 0.0
        
        downside = returns[returns < 0.0]
        sortino = float(returns.mean() / downside.std(ddof=0) * sqrt(12)) if len(downside) > 1 and downside.std(ddof=0) > 0 else 0.0
        
        drawdown = wealth / wealth.cummax() - 1.0
        max_drawdown = abs(float(drawdown.min()))
        calmar = cagr / max_drawdown if max_drawdown > 0.0 else 0.0
        
        benchmark_variance = float(benchmark.var(ddof=0))
        beta = float(np.cov(returns, benchmark, ddof=0)[0, 1] / benchmark_variance) if benchmark_variance > 0.0 else 0.0
        alpha = float((returns.mean() - beta * benchmark.mean()) * 12)
        
        return BacktestMetrics(
            total_return=total_return,
            cagr=cagr,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            max_drawdown=max_drawdown,
            volatility=volatility,
            win_rate=float((returns > 0.0).mean()),
            turnover=total_turnover,
            alpha=alpha,
            beta=beta,
        )


def _sync_holdings(db, portfolio_id: str, current_holdings: dict, as_of_date: date, get_price):
    """Sync the live DB Holdings table so the evaluation uses the updated simulated portfolio."""
    from database.models import HoldingModel
    
    # Clear existing
    db.query(HoldingModel).filter_by(portfolio_id=portfolio_id).delete()
    
    total_val = sum(qty * get_price(t, as_of_date) for t, qty in current_holdings.items())
    if total_val <= 0:
        total_val = 1.0
        
    for ticker, qty in current_holdings.items():
        if qty <= 0 and ticker != "CASH":
            continue
        price = get_price(ticker, as_of_date)
        market_value = qty * price
        holding = HoldingModel(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=qty,
            average_price=price,
            current_price=price,
            market_value=market_value,
            weight=market_value / total_val
        )
        db.add(holding)
    db.commit()
