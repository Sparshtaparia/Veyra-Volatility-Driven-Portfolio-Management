# Research Baseline Issues Log

The following issues were identified during the audit of the Jupyter notebook research baseline (`notebook.ipynb`). 

These issues are documented here for future resolution but are **NOT FIXED** in the current implementation to preserve the quantitative meaning of the existing baseline.

---

### 1. Forward-return/lookahead ambiguity

- **Issue:** The target variable `return_fwd_1m` is calculated as a 1-period shift of `return_1m` on the monthly dataframe. However, the calculation of `return_1m` itself uses a `pct_change(1)` on the month-end close price. This creates an overlapping window where the end-of-month price is used both for the factor calculation and the beginning of the forward return period.
- **Evidence:** `df['return_fwd_1m'] = df.groupby(level='ticker')['return_1m'].shift(-1)`
- **Why it matters:** It can introduce lookahead bias if the factors are assumed to be known at the exact same moment the forward return period begins.
- **Current Status:** **DOCUMENTED — NOT FIXED**

### 2. GARCH return rescaling

- **Issue:** Returns are scaled up by 100 before fitting the GJR-GARCH model, and the resulting conditional volatility is scaled down by 100 after.
- **Evidence:** `r = log_ret.dropna() * 100` and `fitted_vol = (res.conditional_volatility / 100)`
- **Why it matters:** While standard practice to help the `arch` optimizer converge, the manual scaling can introduce precision issues or bugs if the scaling factor is forgotten elsewhere in the pipeline.
- **Current Status:** **DOCUMENTED — NOT FIXED**

### 3. Fama-French beta shift

- **Issue:** The rolling Fama-French betas are shifted by 1 period before being joined to the main feature dataframe.
- **Evidence:** `monthly_df = monthly_df.join(betas.groupby('ticker').shift())`
- **Why it matters:** This is correct from a quantitative perspective to prevent lookahead bias (using a beta estimated at the end of the month as a feature for that same month's forward return). However, it requires explicit validation in the production engine to ensure the alignment remains correct.
- **Current Status:** **DOCUMENTED — NOT FIXED**

### 4. Daily/monthly frequency mismatch

- **Issue:** Technical features (RSI, ATR, MACD, BB) are computed on daily data. GARCH is also fit on the daily series. Both are then aggregated to a monthly level. However, the aggregation method differs (e.g., Dollar Volume is aggregated using a monthly mean, while others use the month-end last value).
- **Evidence:** In `STEP 4C`, `dollar_vol` uses `.resample('M').mean()`, while feature columns use `.resample('M').last()`.
- **Why it matters:** Inconsistent aggregation strategies can lead to noisy signals if the month-end value is an outlier compared to the monthly average.
- **Current Status:** **DOCUMENTED — NOT FIXED**
