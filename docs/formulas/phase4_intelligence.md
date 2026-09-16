# Phase 4 Formulas

For asset excess return `r_i - RF`, the rolling five-factor regression is:

`r_i,t - RF_t = α_i + β_MKT(MKT-RF)_t + β_SMB SMB_t + β_HML HML_t + β_RMW RMW_t + β_CMA CMA_t + ε_i,t`

Only rows dated on or before the evaluation date enter the trailing window.

For factor `j`, production z-score normalization is:

`z_i,j = (F_i,j - mean_j) / population_std_j`

A zero-dispersion cross-section maps to zero. Rank normalization maps stable
ascending ranks linearly to `[-1, 1]`.

The base signal and visible contribution are:

`contribution_i,j = w_j z_i,j`

`S_i = Σ_j contribution_i,j`

Reliability uses the regression `R²` as base reliability. Volatility adjustment
is `max(floor, exp(-k max(volatility_ratio - 1, 0)))`. Regime and recent
performance multipliers are configurable. Effective reliability is the clipped
product of base, volatility, regime, and performance adjustments.

Portfolio risk components are clipped to `[0, 1]`: weighted conditional
volatility relative to its configured reference, weighted maximum drawdown,
mean absolute pairwise correlation, Herfindahl concentration, and inverse
weighted dollar-volume capacity. Composite risk is their configurable weighted
sum.

The state-coupled operator is:

`risk_adjustment = clip(1 - risk_aversion × composite_risk)`

`controlled_signal = base_signal × volatility_adjustment × reliability_adjustment × risk_adjustment`

Every term is returned and persisted.
