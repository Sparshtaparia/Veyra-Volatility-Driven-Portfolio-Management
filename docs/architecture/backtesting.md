# Backtesting & Quantitative Validation

This document describes the backtesting framework used for the Veyra intelligence pipeline.

## Methodology

Veyra uses a **chronological pipeline backtester** that strictly separates past from future data. Instead of generating vectorized signal grids, the backtest runs the exact same `SignalEvaluationService` and `RebalanceService` used in live production, simulated inside an isolated in-memory database.

### Event Loop
For each evaluation date $T$:
1. **State Injection**: The simulated portfolio holdings are synced to the DB.
2. **Phase 1-5**: The pipeline evaluates signals using *only* historical data strictly where $t \le T$. 
3. **Phase 6**: Optimization produces target allocations.
4. **Phase 7**: Paper rebalance executes simulated trades and applies configurable transaction costs and slippage.
5. **Phase 8**: Feedback computes the adaptive threshold error. The new threshold is applied *only* to the next evaluation date $T+1$.

## Lookahead Audit
An extensive lookahead audit was conducted across the quant engine:
- **Features (`technical.py`)**: ATR and MACD calculations correctly use point-in-time EMAs. Tests confirm zero variance when future prices are modified.
- **Returns (`returns.py`)**: Uses explicit `shift(1)` to construct return sequences.
- **Volatility (`gjr_garch.py`)**: Explicitly ignores NaNs and fits models only on observed trailing returns.
- **Thresholds (`threshold.py`)**: Mandates `timestamp <= as_of_date` when querying historical stress observations.

## Survivorship and Data Bias
> [!WARNING]
> The backtest universe is specified manually via configuration (e.g. `["AAPL", "MSFT"]`). If the specified universe represents *current* index constituents (e.g., current S&P 500 members), the resulting performance will exhibit **survivorship bias**. The framework does not currently manage dynamic universe constituents natively.

## Transaction Costs
Configurable defaults:
- **Transaction Cost**: 5 bps (0.05%)
- **Slippage**: 2 bps (0.02%)

Both are deducted from the simulated `CASH` holding at each rebalance. 

## Research vs Production
> [!IMPORTANT]
> Backtest results are solely for **research validation** and tuning hyperparameters (like Phase 8 learning rate $\eta$). Past backtest performance does not guarantee future results. Do not conflate simulated backtest returns with live portfolio performance.
