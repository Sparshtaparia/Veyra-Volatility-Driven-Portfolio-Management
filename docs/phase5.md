# Phase 5 — Portfolio control, feedback, and evaluation

Phase 5 closes Veyra's core decision loop. It consumes the persisted Phase 3
volatility/regime state and Phase 4 controlled signals/risk state. It does not
place live orders.

## Control path

```text
portfolio upload → market/features → GJR-GARCH → regime
                 → factors/reliability/risk → controlled signal
                 → exposure controller → convex optimizer
                 → target weights → paper trades → outcome feedback ↺
```

All production decisions use information available at or before their signal
date. Backtests distinguish signal, rebalance, execution, and return-realization
dates; the signal date must be strictly earlier than the realized return.

## Formulas

Inverse-volatility baseline for asset `i`:

```text
b_i = (1 / σ_i) / Σ_j(1 / σ_j) × target gross exposure
```

The exposure controller remains separate from optimization:

```text
gross target = clip(base exposure × regime factor × (1 - risk sensitivity × R))
```

The long-only convex optimizer minimizes:

```text
baseline_penalty × ||w - b||²
+ turnover_penalty × ||w - current||₁
- signal_strength × Sᵀw
```

subject to non-negative weights, per-stock and per-sector caps, the controlled
gross-exposure ceiling, minimum cash, and the annualized portfolio-volatility
target. With diagonal covariance, `Σ = diag((σ_i √252)²)`.

Paper execution applies side-aware slippage and explicit transaction costs.
The feedback controller implements `X(t+1) = F(X(t), u(t), Y(t+1))` as a
deterministic exponentially weighted update to the volatility distribution,
adaptive threshold, reliability multiplier, risk limit, exposure limit, and
portfolio value. Every prior state, outcome, signal, and updated state is saved.

Backtest returns are net of `turnover × (transaction_cost_bps + slippage_bps)`.
Metrics include total return, CAGR, Sharpe, Sortino, Calmar, maximum drawdown,
annualized volatility, win rate, turnover, alpha, and beta. Attribution is the
cumulative weighted return by asset.

## Ablations

The runner requires all seven variants in one comparable batch:

- base multi-factor
- no GARCH
- GARCH sizing only
- no regime control
- no reliability
- no risk coupling
- full state-coupled architecture

The caller supplies target-weight histories for each variant, keeping the
backtester independent from strategy construction and making every comparison
explicit.

## Persistence

Migration `0003_phase5_portfolio_control` adds only the requested tables:

- `portfolio_targets`
- `rebalance_events`
- `trades`
- `portfolio_snapshots`
- `feedback_updates`
- `backtests`
- `backtest_returns`
- `backtest_metrics`

Evaluation-correlated records use the existing `evaluation_id`. The same
SQLAlchemy sessions and PostgreSQL-compatible UUID/JSON columns used by earlier
phases are retained; there is no Supabase-specific database code.

## API

- `POST /api/v1/portfolios/upload` — multipart CSV/XLSX import
- `POST /api/v1/portfolios/manual` — manual holding import
- `GET /api/v1/portfolios/{portfolio_id}/holdings`
- `POST /api/v1/portfolios/{portfolio_id}/optimize` — optimize and paper rebalance
- `GET /api/v1/evaluations/{evaluation_id}/portfolio-control`
- `POST /api/v1/portfolios/{portfolio_id}/feedback`
- `GET /api/v1/portfolios/{portfolio_id}/feedback`
- `POST /api/v1/backtests`
- `GET /api/v1/backtests/{backtest_id}`
- `POST /api/v1/backtests/ablation`

Optimizer, exposure, transaction-cost, and slippage settings are request-visible
and validated. Defaults are defined in typed Pydantic configuration models.

## Quant terminal

The React/TypeScript terminal uses Tailwind, shadcn-style local UI primitives,
Plotly, TanStack Query, and TanStack Table. It includes Dashboard, My Portfolio,
Factor Lab, Volatility Lab, Regime Explorer, Risk Monitor, State-Coupled Decision
Engine, Portfolio Optimizer, Rebalancing, Backtest & Performance, and Feedback
Monitor. The decision page renders the complete signal adjustment chain and the
feedback page renders previous state → observed outcome → updated state.

## Deployment

For local containers, run `docker compose up --build`; the terminal is exposed
on port 8080 and the API on 8000. The API container runs Alembic before startup.
For Supabase, set `DATABASE_URL` to the SQLAlchemy PostgreSQL URL supplied by the
project (including SSL parameters when required), set `CORS_ORIGINS` as a JSON
array, mount/provide the Fama-French CSV, and run `alembic upgrade head` before
starting workers. `/health` is a liveness check and `/health/ready` verifies a
database round trip. No credentials belong in the repository or frontend build.

## Known limitations

- The optimizer uses a diagonal covariance approximation; cross-asset covariance
  enters Phase 4 risk scoring but not the Phase 5 variance constraint.
- Upload pricing uses the most recent provider close on or before the requested
  date. There is no corporate-action reconciliation or tax-lot accounting.
- Paper fills use deterministic bps slippage, not a limit-order or volume-impact
  model.
- Ablation construction is explicit input; automated historical rebuilding of
  all seven strategy variants is a future research orchestration layer.
- The API currently runs backtests synchronously and is suitable for moderate
  research datasets, not distributed batch grids.
- The browser bundle includes Plotly and is intentionally feature-rich; route
  code splitting is a future frontend performance improvement.
- Live optimization, broker execution, and final trade authorization are outside
  this phase by design.
