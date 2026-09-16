# Phase 5: Reliability & Composite Risk Engine

## Overview
Phase 5 introduces explicit risk management and signal reliability attenuation into the quantitative engine pipeline. 

The flow expands to:
Features → Volatility/Regime → Base Signal → Signal Regulation → **Phase-5 Reliability + Composite Risk** → State-Coupled Control

## Reliability Engine
The Reliability Engine (`quant_engine/reliability/`) provides an asset-level measure of signal confidence based on the current volatility state.

### Formula
`W_{i,t} = \exp(-\kappa \cdot \sigma_{i,t})`

Where:
- `\sigma_{i,t}` is the forecast volatility for the asset
- `\kappa` is a configurable parameter (default: 1.0) controlling the attenuation rate.

Higher instability/volatility reduces reliability smoothly, bounding the score between 0 and 1. The score is mapped to a discrete `ReliabilityState` (HIGH, MODERATE, LOW) for consumption by the State-Coupled Control.

## Composite Risk Engine
The Composite Risk Engine (`quant_engine/risk/`) computes a portfolio-level aggregated risk state using available asset data.

### Components
Currently supported and explicitly weighted components:
1. **Volatility Exposure:** `1.0 - \exp(-0.5 \cdot \text{avg\_vol})`, bounding the weighted average asset volatility.
2. **Concentration:** Computed using the normalized Herfindahl-Hirschman Index (HHI) of the portfolio weights.

### Aggregation
The composite risk score is a linear combination of components with an explicit nonlinear penalty for the interaction between high volatility and high concentration.
The final bounded score (0 to 1) is mapped to a discrete `RiskState` (LOW, MODERATE, ELEVATED, CRITICAL).

## State-Coupled Control Operator
The `StateCoupledControl` (Phase 4) consumes these explicit states to apply deterministic multipliers to the regulated signal:
- `risk_multipliers`: Attenuates portfolio-wide signals based on aggregate risk.
- `reliability_multipliers`: Attenuates asset-specific signals based on its reliability score.

## Future Phases
Optimization, rebalancing execution, automated feedback loops, backtesting, and rule-based triggers are out of scope for Phase 5 and are designated for Phase 6+.
