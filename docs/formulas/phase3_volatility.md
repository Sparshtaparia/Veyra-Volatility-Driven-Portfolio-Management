# Phase 3 Volatility Model

Phase 3 converts chronological daily return series into asset-level
`VolatilityEstimate` objects, aggregates them into a cross-sectional market
stress score, and classifies that score against an adaptive historical
threshold. Persistence and API integration remain Phase 3D work.

## Research methodology

The research notebook calculates log returns from closing prices and fits each
ticker independently with `arch_model` using:

- GARCH volatility with `p=1`, `o=1`, and `q=1`
- the library's default constant-mean model
- Normal residual innovations
- returns multiplied by 100 before fitting
- `rescale=False`
- at least 252 observations
- a trailing 21-observation standard deviation as realized volatility

The notebook converts fitted conditional volatility back to decimal units by
dividing by 100. Its per-asset volatility ratio is conditional GJR-GARCH
volatility divided by trailing 21-observation realized volatility.

## ARCH, GARCH, and GJR-GARCH

An ARCH model makes current conditional variance depend on prior squared
shocks. A GARCH(1,1) model adds prior conditional variance:

```text
sigma_t^2 = omega + alpha * epsilon_(t-1)^2 + beta * sigma_(t-1)^2
```

Symmetric GARCH assigns the same variance effect to equally sized positive and
negative shocks. GJR-GARCH(1,1) adds an indicator for negative shocks:

```text
sigma_t^2 = omega
          + alpha * epsilon_(t-1)^2
          + gamma * I(epsilon_(t-1) < 0) * epsilon_(t-1)^2
          + beta * sigma_(t-1)^2
```

- `omega` is the positive long-run variance intercept.
- `alpha` measures sensitivity to the latest squared shock.
- `gamma` is the additional effect when the latest shock is negative.
- `beta` measures persistence from the previous conditional variance.

A positive shock contributes `alpha * epsilon^2`; an equally sized negative
shock contributes `(alpha + gamma) * epsilon^2`. Veyra uses GJR-GARCH because
equity volatility commonly responds asymmetrically to negative returns, which
symmetric GARCH cannot represent.

With symmetric Normal innovations, a shock is negative with probability one
half. Veyra therefore defines expected-shock persistence as:

```text
alpha + beta + gamma / 2
```

This is the full GJR persistence measure under the stated distributional
assumption, not merely the symmetric-GARCH `alpha + beta` measure.

## Software implementation details

`GJRGarchEngine` accepts decimal returns, where `0.02` means a two-percent
return. It requires a chronological, duplicate-free `pandas.Series` with a
`DatetimeIndex`. It rejects infinities, non-numeric values, and constant or
near-constant histories. NaNs are dropped without forward filling and the count
is recorded in diagnostics.

The default minimum history is 252 usable observations, matching the notebook
and representing approximately one trading year. The setting is configurable,
but cannot be shorter than the realized-volatility window. When `as_of_date` is
provided, observations after that cutoff are removed before validation and
fitting, preventing lookahead.

Returns are multiplied by 100 at the `arch` boundary. Public values use decimal
units throughout:

- conditional and forecast volatility are divided by 100;
- conditional variance is the square of decimal conditional volatility;
- `omega`, which has variance units, is divided by `100^2`;
- `alpha`, `gamma`, and `beta` are dimensionless and require no rescaling.

The returned conditional volatility is the latest fitted value at time `t`.
The forecast is the square root of the one-step-ahead (`t+1`) variance forecast.
Neither is annualized. Realized volatility is the sample standard deviation
(`ddof=1`) of the latest 21 available returns at or before `t`. The asset-level
ratio is conditional volatility divided by this realized volatility.

Optimizer warnings are captured in `GARCHDiagnostics`, not printed. A non-zero
convergence flag or third-party fitting failure produces an explicit fallback
estimate by default: conditional, forecast, and realized volatility all use the
trailing realized value, the ratio is `1.0`, parameters are absent, and the
diagnostics status is `FALLBACK`. This reproduces the notebook's fallback idea
without hiding the failure. Strict callers can disable fallback and receive a
`GARCHFitError` or `GARCHConvergenceError`; raw `arch` exceptions never cross
the volatility-engine boundary.

## Cross-sectional market stress

For each eligible asset, the Phase 3B ratio is:

```text
volatility_ratio_i = conditional_volatility_i / realized_volatility_i
```

A ratio near `1` means modeled conditional volatility is close to recent
realized volatility. Values above `1` indicate elevated modeled volatility;
values below `1` indicate relatively subdued volatility.

At each timestamp, Veyra defines the market stress score as the cross-sectional
median:

```text
stress_score_t = median(volatility_ratio_1,t, ..., volatility_ratio_n,t)
```

The median is used because a single unstable fit or extreme ticker should not
dominate the market state. Aggregate volatility is likewise the median
conditional volatility. The snapshot also records median realized volatility
and volatility-ratio interquartile range.

Successful GJR-GARCH fits are eligible by default. Rolling-volatility fallback
estimates are counted and reported but excluded from the score unless
`include_fallbacks_in_aggregation=True` is configured explicitly. Estimates
with the wrong timestamp, non-finite values, non-positive ratios, or non-success
statuses are excluded. Missing per-ticker estimates count as failures.

The implementation defaults require at least three eligible assets and 50%
coverage. Both values are configurable implementation safeguards, not research
or patented-methodology constants. Coverage, fit coverage, fallback coverage,
and excluded counts are included in the stress snapshot. Insufficient coverage
raises an explicit `InsufficientCoverageError` rather than producing a regime.

## Research mode and production adaptive mode

The research notebook calculates the daily cross-sectional median GARCH
volatility ratio and then takes the 75th percentile over the full resulting
sample. In the recorded notebook run this was approximately `1.197`; dates with
stress strictly above that value were labeled high stress. Because the full
sample includes future dates relative to earlier classifications, that method
is retained only as the explicit `FixedThresholdStrategy` compatibility mode.
The fixed value must be supplied by the caller and is never a global default.

Production uses `RollingQuantileThreshold`. At time `t`, it computes boundaries
from only the trailing stress observations with timestamps less than or equal
to `t`:

```text
low_t    = rolling quantile(stress, 0.25)
center_t = rolling quantile(stress, 0.50)
high_t   = rolling quantile(stress, 0.75)
```

The implementation defaults are a 63-observation window, 21-observation
minimum history, and quantiles `0.25`, `0.50`, and `0.75`. Window length,
minimum history, and every quantile are configurable. These defaults are
software choices, not claims about the research or patented methodology.

Classification uses the derived boundaries:

- `LOW_VOL`: score is strictly below the lower quantile.
- `NORMAL`: score is between the lower quantile and historical median,
  including both boundaries.
- `ELEVATED`: score is above the median but below the high threshold.
- `HIGH_STRESS`: score is greater than or equal to the high threshold.

`distance_to_threshold` is the signed difference `stress_score - high_t`; it is
not presented as a confidence percentage.

The regime service replaces any same-date historical item with the current
snapshot and ignores observations after the classification date. Threshold
strategies independently filter to timestamps at or before `t`. Tests verify
that appending or changing future values cannot change an earlier threshold or
regime.
