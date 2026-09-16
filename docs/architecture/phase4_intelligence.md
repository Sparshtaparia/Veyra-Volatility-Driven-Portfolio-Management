# Phase 4 Intelligence and State-Coupled Signals

```text
Portfolio + Market Data + Fama-French Returns
    ↓
Phase 2 FeatureService + Phase 3 Volatility/Regime
    ↓
Rolling Five-Factor Exposures (data <= evaluation date)
    ↓
Cross-Sectional Factor Normalization
    ↓
Configurable Base Signal and Contributions
    ↓
Reliability + Portfolio Risk State
    ↓
Deterministic State-Coupled Operator
    ↓
Five Phase 4 Tables → FastAPI DTOs
```

The production normalization default is cross-sectional population z-score.
It makes heterogeneous factor scales comparable while preserving direction and
relative magnitude. Percentile-rank normalization mapped to `[-1, 1]` is also
available for research and outlier-resistant configurations.

Fama-French inputs are supplied through `FactorDataProvider`. The production
dependency reads a configured decimal-return CSV using `FAMA_FRENCH_DATA_PATH`.
Required columns are `date`, `MKT-RF`, `SMB`, `HML`, `RMW`, `CMA`, and `RF`.
No vendor-specific or Supabase-specific data access is embedded in the engine.

All factor weights, reliability sensitivities/regime adjustments, risk
component weights/reference levels, and operator risk aversion are typed
configuration. The explainability payload contains the values needed by a
frontend; clients do not reproduce quant calculations.

Phase 4 persists `factor_states`, `fama_french_exposures`,
`reliability_states`, `risk_states`, and `controlled_signals`, correlated by
the existing evaluation ID. The five-table Phase 4 bundle is flushed and
committed atomically. A completed repeated evaluation ID returns persisted
results.

This phase produces controlled signals only. It does not translate signals
into target weights, optimize a portfolio, make a rebalance decision, or
execute orders.
