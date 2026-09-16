"""Cross-sectional normalization without mixing arbitrary raw scales."""

from collections.abc import Mapping

import numpy as np
from scipy.stats import rankdata

from quant_engine.factors.models import NormalizationMethod


def normalize_cross_section(
    values_by_ticker: Mapping[str, Mapping[str, float]],
    method: NormalizationMethod = NormalizationMethod.Z_SCORE,
) -> dict[str, dict[str, float]]:
    if not values_by_ticker:
        raise ValueError("factor cross-section must not be empty")
    key_sets = [set(values) for values in values_by_ticker.values()]
    if any(keys != key_sets[0] for keys in key_sets[1:]):
        raise ValueError("every ticker must provide the same factor keys")
    factor_names = key_sets[0]
    if not factor_names:
        raise ValueError("tickers must share at least one factor")
    output: dict[str, dict[str, float]] = {ticker: {} for ticker in values_by_ticker}
    for factor in sorted(factor_names):
        tickers = sorted(values_by_ticker)
        values = np.asarray([values_by_ticker[ticker][factor] for ticker in tickers], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"factor {factor!r} contains a non-finite value")
        if method is NormalizationMethod.Z_SCORE:
            scale = float(values.std(ddof=0))
            normalized = np.zeros_like(values) if scale == 0.0 else (values - values.mean()) / scale
        else:
            ranks = rankdata(values, method="average") - 1.0
            normalized = (
                np.zeros_like(values)
                if len(values) == 1
                else (ranks / (len(values) - 1)) * 2.0 - 1.0
            )
        for ticker, value in zip(tickers, normalized, strict=True):
            output[ticker][factor] = float(value)
    return output
