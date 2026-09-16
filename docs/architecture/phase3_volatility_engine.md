# Phase 3 Volatility Engine

```text
Market Data
    ↓
Chronological Returns
    ↓
GJR-GARCH(1,1) per Asset
    ↓
VolatilityEstimate[]
    ↓
Eligibility and Coverage Checks
    ↓
Cross-Sectional Median Volatility Ratio
    ↓
Market Stress Snapshot
    ↓
Rolling Historical Stress Distribution
    ↓
Adaptive Quantile Thresholds
    ↓
Four-State Regime Classification
    ↓
MarketVolatilityState
    ↓
VolatilityRepository + RegimeRepository
    ↓
Supabase PostgreSQL
    ↓
FastAPI response contracts
```

## Component boundaries

- `GJRGarchEngine` owns only per-asset model fitting and fallback generation.
- `VolatilityService` isolates ticker failures and coordinates per-asset fits.
- `VolatilityAggregator` owns eligibility, coverage, counts, and robust medians.
- `RollingQuantileThreshold` and `FixedThresholdStrategy` own threshold policy.
- `RegimeClassifier` maps stress and boundaries into the four regime states.
- `RegimeService` combines the current snapshot with historical stress and
  returns `MarketVolatilityState`.
- `VolatilityEvaluationService` loads the portfolio universe and market data,
  invokes the quantitative services, supplies persisted stress history, and
  controls the write transaction.
- `VolatilityRepository` persists and retrieves per-asset estimates.
- `RegimeRepository` persists regimes and returns chronological stress history.
- FastAPI routes translate application DTOs into stable response schemas.

Quantitative components do not persist data or depend on FastAPI. The database
is accessed through SQLAlchemy using the existing `DATABASE_URL`; Supabase is
treated as hosted PostgreSQL and no Supabase SDK is used. Phase 3 does not
change portfolio weights or make rebalance decisions.

## Persistence

`volatility_states` stores one row per evaluation, ticker, and date, including
the fitted parameters, volatility outputs, diagnostics, and fallback marker.
That compound key is unique.

`regime_states` stores one cross-sectional state per evaluation and date,
including breadth counts, aggregate measures, adaptive threshold, regime, and
coverage. Historical queries are chronological and restricted to dates on or
before the requested evaluation date. `RegimeService` applies the stricter
`timestamp < current` rule before appending the current snapshot, preventing
same-day duplication and future leakage.

The per-asset rows and final regime row are flushed by their repositories and
committed together by `VolatilityEvaluationService`. A failed regime write
rolls back the asset rows. Reusing an evaluation ID returns its existing result;
an ID associated with another portfolio or date is rejected.

## API

- `POST /api/v1/portfolios/{portfolio_id}/volatility/evaluate`
- `GET /api/v1/evaluations/{evaluation_id}/volatility`
- `GET /api/v1/evaluations/{evaluation_id}/regime`
- `GET /api/v1/portfolios/{portfolio_id}/regime/latest`

The default rolling threshold requires 21 observations including the current
snapshot. A portfolio therefore needs historical regime states (for example,
from a controlled backfill) before its first adaptive evaluation can complete.
The explicit fixed-threshold research mode remains available in the quant
layer but is not selected implicitly by the API.

## Phase 4 decision extension

```text
Phase 2 FeatureSnapshot
    ↓
Interpretable RSI + ATR-normalized MACD base signal
    ↓
Volatility-conditioned attenuation (Phase 3 regime and asset ratio)
    ↓
State-coupled control: U = Phi(S, volatility, risk_state, reliability_state)
    ↓
HOLD / REVIEW / ADAPT decision state
```

`SignalService` produces bounded, deterministic, interpretable base signals.
`SignalRegulator` preserves orientation and multiplies signal amplitude by a
strictly positive factor no greater than one. NORMAL and LOW_VOL retain the
base signal; ELEVATED and HIGH_STRESS apply increasing ratio-based decay.
`StateCoupledControl` applies the remaining regime control multiplier and
returns concise reason codes. Risk and reliability are explicitly neutral typed
states in Phase 4; their substantive engines, plus optimization, rebalancing,
feedback, and backtesting, are later phases.

`POST /api/v1/portfolios/{portfolio_id}/signals/evaluate` composes the existing
Phase 3 persisted evaluation with feature generation and the Phase 4 controls.
