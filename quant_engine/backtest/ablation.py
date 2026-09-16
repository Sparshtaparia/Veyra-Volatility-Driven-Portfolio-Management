"""Comparable execution of the seven required architecture ablations."""

import pandas as pd

from quant_engine.backtest.engine import BacktestEngine
from quant_engine.backtest.models import AblationVariant, BacktestResult


class AblationRunner:
    def __init__(self, engine: BacktestEngine | None = None) -> None:
        self.engine = engine or BacktestEngine()

    def run(
        self,
        asset_returns: pd.DataFrame,
        benchmark_returns: pd.Series,
        variant_weights: dict[AblationVariant, pd.DataFrame],
    ) -> dict[AblationVariant, BacktestResult]:
        missing = set(AblationVariant) - set(variant_weights)
        if missing:
            raise ValueError(f"missing ablation variants: {sorted(item.value for item in missing)}")
        return {
            variant: self.engine.run(
                variant.value,
                asset_returns,
                variant_weights[variant],
                benchmark_returns,
            )
            for variant in AblationVariant
        }
