# Phase 2 Features

This document outlines the features implemented in Phase 2, comparing the research notebook logic against the production implementation.

## Features Implemented

### 1. Relative Strength Index (RSI)
- **Formula:** Wilder's Smoothing on up/down price changes.
- **Parameters:** `length=14`
- **Frequency:** Daily
- **Missing Data:** Emits `NaN` for first 14 periods.
- **Notebook Parity:** Matches exactly (`ta.rsi`). Production implements pure pandas EWM to minimize external dependencies.

### 2. Average True Range (ATR)
- **Formula:** True Range smoothed by Wilder's Moving Average.
- **Parameters:** `length=14`
- **Frequency:** Daily
- **Missing Data:** Emits `NaN` until history allows calculation.
- **Notebook Parity:** **DIFFERENCE EXPLAINED**. The notebook applies a full-sample Z-score to ATR (`(atr_raw - atr_raw.mean()) / atr_raw.std()`). This introduces lookahead bias because the mean and std use future data. The production implementation returns **raw ATR**.

### 3. MACD Histogram
- **Formula:** Fast EMA - Slow EMA. Histogram = MACD - Signal EMA.
- **Parameters:** `fast=12`, `slow=26`, `signal_len=9`
- **Frequency:** Daily
- **Missing Data:** Returns `NaN` for the first 25 periods.
- **Notebook Parity:** **DIFFERENCE EXPLAINED**. Similar to ATR, the notebook applies a full-sample Z-score to the MACD histogram. Production returns the **raw MACD Histogram** to ensure lookahead safety.

### 4. Bollinger Band Width
- **Formula:** `(Upper Band - Lower Band) / Middle Band`
- **Parameters:** `length=20`, `num_std=2.0`
- **Frequency:** Daily
- **Missing Data:** Emits `NaN` for first 19 periods.
- **Notebook Parity:** Matches exactly.

### 5. Dollar Volume
- **Formula:** `Close * Volume`
- **Frequency:** Daily
- **Missing Data:** Assumes 0 if volume is missing, else calculates based on available data.
- **Notebook Parity:** Matches exactly. (Note: the notebook subsequently rolls this into a 5-year monthly mean for liquidity ranking. In Phase 2, we output daily Dollar Volume; the aggregation happens at the portfolio/universe construction phase).

## Lookahead Safety Policy
Every feature is calculated strictly using data up to timestamp `t`. Production tests ensure that mutating `t+10` data has zero effect on feature values at `t`. Z-score normalizations must be performed *cross-sectionally* in Phase 4/5, not longitudinally over the full historical sample.
