"""Lookahead-safe rolling Fama-French five-factor exposure estimation."""

from datetime import date

import numpy as np
import pandas as pd

from quant_engine.factors.models import FamaFrenchExposure

FACTOR_COLUMNS = ("MKT-RF", "SMB", "HML", "RMW", "CMA")


class FamaFrenchEstimator:
    def __init__(self, window: int = 252, minimum_observations: int = 60) -> None:
        if window < minimum_observations or minimum_observations < 6:
            raise ValueError("window must be >= minimum_observations >= 6")
        self.window = window
        self.minimum_observations = minimum_observations

    def estimate(
        self,
        ticker: str,
        asset_returns: pd.Series,
        factor_returns: pd.DataFrame,
        as_of_date: date,
    ) -> FamaFrenchExposure:
        cutoff = pd.Timestamp(as_of_date)
        factors = self._normalize_columns(factor_returns)
        joined = pd.concat(
            [asset_returns.rename("asset_return"), factors], axis=1, join="inner"
        ).sort_index()
        joined = joined.loc[joined.index <= cutoff].dropna().tail(self.window)
        if len(joined) < self.minimum_observations:
            raise ValueError(
                f"Fama-French regression requires {self.minimum_observations} observations; "
                f"received {len(joined)}"
            )

        excess = joined["asset_return"] - joined["RF"]
        design = np.column_stack(
            [np.ones(len(joined)), joined.loc[:, FACTOR_COLUMNS].to_numpy(dtype=float)]
        )
        coefficients, _, _, _ = np.linalg.lstsq(design, excess.to_numpy(dtype=float), rcond=None)
        fitted = design @ coefficients
        residual = excess.to_numpy(dtype=float) - fitted
        total = float(np.sum((excess - excess.mean()) ** 2))
        r_squared = (
            1.0 if total == 0.0 else max(0.0, min(1.0, 1.0 - float(residual @ residual) / total))
        )
        return FamaFrenchExposure(
            ticker=ticker,
            as_of_date=as_of_date,
            alpha=float(coefficients[0]),
            market_beta=float(coefficients[1]),
            smb_beta=float(coefficients[2]),
            hml_beta=float(coefficients[3]),
            rmw_beta=float(coefficients[4]),
            cma_beta=float(coefficients[5]),
            r_squared=r_squared,
            observation_count=len(joined),
        )

    @staticmethod
    def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
        aliases = {column.upper().replace("_", "-"): column for column in frame.columns}
        required = (*FACTOR_COLUMNS, "RF")
        missing = [column for column in required if column not in aliases]
        if missing:
            raise ValueError(f"missing Fama-French columns: {', '.join(missing)}")
        normalized = frame[[aliases[column] for column in required]].copy()
        normalized.columns = list(required)
        if not isinstance(normalized.index, pd.DatetimeIndex):
            normalized.index = pd.to_datetime(normalized.index)
        return normalized.apply(pd.to_numeric, errors="coerce")
