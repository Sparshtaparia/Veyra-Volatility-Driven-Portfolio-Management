"""Lookahead-safe monthly walk-forward backtest engine."""

from math import sqrt

import numpy as np
import pandas as pd

from quant_engine.backtest.models import (
    AttributionItem,
    BacktestConfig,
    BacktestMetrics,
    BacktestResult,
    BacktestReturn,
)


class BacktestEngine:
    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(
        self,
        name: str,
        asset_returns: pd.DataFrame,
        target_weights: pd.DataFrame,
        benchmark_returns: pd.Series,
    ) -> BacktestResult:
        returns = asset_returns.sort_index().dropna(how="all")
        weights = target_weights.sort_index()
        benchmark = benchmark_returns.sort_index()
        if returns.empty or weights.empty:
            raise ValueError("backtest inputs must not be empty")
        if not isinstance(returns.index, pd.DatetimeIndex) or not isinstance(
            weights.index, pd.DatetimeIndex
        ):
            raise ValueError("backtest inputs require DatetimeIndex")
        current = pd.Series(0.0, index=returns.columns)
        records: list[BacktestReturn] = []
        contributions = pd.Series(0.0, index=returns.columns)
        last_month = None
        active_signal_date = None
        active_rebalance_date = None
        for position, realization_date in enumerate(returns.index):
            if position == 0:
                continue
            month = (realization_date.year, realization_date.month)
            turnover = 0.0
            cost = 0.0
            if month != last_month:
                available = weights.loc[weights.index < realization_date]
                if not available.empty:
                    active_signal_date = available.index[-1]
                    proposed = (
                        available.iloc[-1].reindex(returns.columns).fillna(0.0).clip(lower=0.0)
                    )
                    if proposed.sum() > 1.0:
                        proposed = proposed / proposed.sum()
                    turnover = float((proposed - current).abs().sum())
                    cost = (
                        turnover
                        * (self.config.transaction_cost_bps + self.config.slippage_bps)
                        / 10_000.0
                    )
                    current = proposed
                    active_rebalance_date = realization_date
                last_month = month
            if active_signal_date is None or active_rebalance_date is None:
                continue
            row = returns.loc[realization_date].fillna(0.0)
            gross = float(current @ row)
            contributions = contributions.add(current * row, fill_value=0.0)
            records.append(
                BacktestReturn(
                    signal_date=active_signal_date.date(),
                    rebalance_date=active_rebalance_date.date(),
                    execution_date=active_rebalance_date.date(),
                    return_realization_date=realization_date.date(),
                    gross_return=gross,
                    net_return=gross - cost,
                    benchmark_return=float(benchmark.get(realization_date, 0.0)),
                    turnover=turnover,
                    transaction_cost=cost,
                )
            )
        if not records:
            raise ValueError("backtest produced no realized returns")
        net = pd.Series([item.net_return for item in records])
        benchmark_values = pd.Series([item.benchmark_return for item in records])
        metrics = self._metrics(net, benchmark_values, sum(item.turnover for item in records))
        return BacktestResult(
            name=name,
            start_date=records[0].return_realization_date,
            end_date=records[-1].return_realization_date,
            returns=records,
            metrics=metrics,
            attribution=[
                AttributionItem(ticker=ticker, cumulative_contribution=float(value))
                for ticker, value in contributions.items()
            ],
        )

    def _metrics(
        self, returns: pd.Series, benchmark: pd.Series, total_turnover: float
    ) -> BacktestMetrics:
        periods = len(returns)
        wealth = (1.0 + returns).cumprod()
        total_return = float(wealth.iloc[-1] - 1.0)
        years = periods / self.config.annualization_factor
        cagr = float(wealth.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
        volatility = float(returns.std(ddof=0) * sqrt(self.config.annualization_factor))
        sharpe = (
            float(returns.mean() / returns.std(ddof=0) * sqrt(self.config.annualization_factor))
            if returns.std(ddof=0) > 0
            else 0.0
        )
        downside = returns[returns < 0.0]
        sortino = (
            float(returns.mean() / downside.std(ddof=0) * sqrt(self.config.annualization_factor))
            if len(downside) > 1 and downside.std(ddof=0) > 0
            else 0.0
        )
        drawdown = wealth / wealth.cummax() - 1.0
        max_drawdown = abs(float(drawdown.min()))
        calmar = cagr / max_drawdown if max_drawdown > 0.0 else 0.0
        benchmark_variance = float(benchmark.var(ddof=0))
        beta = (
            float(np.cov(returns, benchmark, ddof=0)[0, 1] / benchmark_variance)
            if benchmark_variance > 0.0
            else 0.0
        )
        alpha = float((returns.mean() - beta * benchmark.mean()) * self.config.annualization_factor)
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
