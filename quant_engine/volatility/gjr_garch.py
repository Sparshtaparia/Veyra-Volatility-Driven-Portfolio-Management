"""Production GJR-GARCH(1,1) volatility engine.

Input returns and all public volatility outputs use decimal units: ``0.02``
means two percent. Returns are multiplied by 100 only while interacting with
``arch`` for numerical stability, matching the research notebook.
"""

from __future__ import annotations

import warnings
from datetime import date, datetime
from math import isfinite, sqrt
from typing import Any, Literal

import numpy as np
import pandas as pd
from arch import arch_model
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from quant_engine.volatility.exceptions import (
    GARCHConvergenceError,
    GARCHFitError,
    InsufficientHistoryError,
    InvalidReturnsError,
)
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    VolatilityEstimate,
)


class GJRGarchEngine:
    """Fit a notebook-compatible GJR-GARCH(1,1) model to daily returns.

    The default minimum of 252 usable observations represents approximately
    one trading year and reproduces the research notebook. NaNs are dropped
    explicitly and reported in diagnostics; values are never forward-filled.

    By default, optimizer or third-party failures return a clearly marked
    21-observation rolling-volatility fallback so one asset cannot abort a
    future cross-sectional run. Set ``fallback_on_failure=False`` to receive a
    domain exception instead.
    """

    MODEL_ORDER = (1, 1, 1)  # p, o, q: o=1 is the asymmetric GJR term.
    MEAN_MODEL: Literal["Constant"] = "Constant"
    RESIDUAL_DISTRIBUTION: Literal["normal"] = "normal"
    RETURN_SCALE = 100.0

    def __init__(
        self,
        min_observations: int = 252,
        realized_window: int = 21,
        *,
        fallback_on_failure: bool = True,
        variance_tolerance: float = 1e-12,
    ) -> None:
        if realized_window < 2:
            raise ValueError("realized_window must be at least 2")
        if min_observations < realized_window:
            raise ValueError("min_observations must be >= realized_window")
        if variance_tolerance < 0.0 or not isfinite(variance_tolerance):
            raise ValueError("variance_tolerance must be finite and non-negative")

        self.min_observations = min_observations
        self.realized_window = realized_window
        self.fallback_on_failure = fallback_on_failure
        self.variance_tolerance = variance_tolerance

    def fit(
        self,
        ticker: str,
        returns: pd.Series,
        as_of_date: date | datetime | None = None,
    ) -> VolatilityEstimate:
        """Return the volatility estimate known at ``as_of_date``.

        Observations strictly after ``as_of_date`` are removed before content
        validation or fitting, ensuring they cannot affect an earlier result.
        """

        cleaned, timestamp, input_warnings = self._prepare_returns(returns, as_of_date)
        realized_volatility = self._realized_volatility(cleaned)
        scaled_returns = cleaned * self.RETURN_SCALE
        captured_warnings: list[str] = []
        warning_records: list[warnings.WarningMessage] = []

        try:
            with warnings.catch_warnings(record=True) as warning_records:
                warnings.simplefilter("always")
                result = self._fit_model(scaled_returns)
            captured_warnings = [str(record.message) for record in warning_records]

            convergence_flag = int(result.convergence_flag)
            if convergence_flag != 0:
                error = GARCHConvergenceError(
                    f"GJR-GARCH optimizer did not converge for {ticker!r}; "
                    f"convergence flag={convergence_flag}"
                )
                if not self.fallback_on_failure:
                    raise error
                return self._fallback_estimate(
                    ticker=ticker,
                    timestamp=timestamp,
                    realized_volatility=realized_volatility,
                    observation_count=len(cleaned),
                    convergence_status=GARCHConvergenceStatus.NOT_CONVERGED,
                    warnings=input_warnings + captured_warnings,
                    errors=[str(error)],
                    log_likelihood=self._optional_finite_float(result.loglikelihood),
                )

            return self._build_estimate(
                ticker=ticker,
                timestamp=timestamp,
                cleaned_returns=cleaned,
                result=result,
                warnings=input_warnings + captured_warnings,
            )
        except GARCHConvergenceError:
            raise
        except Exception as exc:
            captured_warnings = [str(record.message) for record in warning_records]
            fit_error = GARCHFitError(f"GJR-GARCH fit failed for {ticker!r}: {exc}")
            if not self.fallback_on_failure:
                raise fit_error from exc
            return self._fallback_estimate(
                ticker=ticker,
                timestamp=timestamp,
                realized_volatility=realized_volatility,
                observation_count=len(cleaned),
                convergence_status=GARCHConvergenceStatus.NOT_APPLICABLE,
                warnings=input_warnings + captured_warnings,
                errors=[str(fit_error)],
            )

    def _fit_model(self, scaled_returns: pd.Series) -> Any:
        p, o, q = self.MODEL_ORDER
        model = arch_model(
            scaled_returns,
            mean=self.MEAN_MODEL,
            vol="GARCH",
            p=p,
            o=o,
            q=q,
            dist=self.RESIDUAL_DISTRIBUTION,
            rescale=False,
        )
        return model.fit(disp="off", show_warning=True)

    def _prepare_returns(
        self,
        returns: pd.Series,
        as_of_date: date | datetime | None,
    ) -> tuple[pd.Series, date, list[str]]:
        if not isinstance(returns, pd.Series):
            raise InvalidReturnsError("returns must be a pandas Series")
        if returns.empty:
            raise InvalidReturnsError("returns must not be empty")
        if not isinstance(returns.index, pd.DatetimeIndex):
            raise InvalidReturnsError("returns must use a pandas DatetimeIndex")

        sliced, timestamp = self._slice_as_of(returns, as_of_date)
        if sliced.empty:
            raise InvalidReturnsError("returns contain no observations at or before as_of_date")
        if sliced.index.has_duplicates:
            raise InvalidReturnsError("returns must not contain duplicate timestamps")
        if not sliced.index.is_monotonic_increasing:
            raise InvalidReturnsError("returns must be in chronological order")
        if is_bool_dtype(sliced.dtype) or not is_numeric_dtype(sliced.dtype):
            raise InvalidReturnsError("returns must contain numerical values")

        values = sliced.to_numpy(dtype=float, copy=False)
        if np.isinf(values).any():
            raise InvalidReturnsError("returns must not contain infinite values")

        missing_count = int(sliced.isna().sum())
        cleaned = sliced.dropna().astype(float)
        if cleaned.empty:
            raise InvalidReturnsError("returns contain no finite observations")
        if len(cleaned) < self.min_observations:
            raise InsufficientHistoryError(len(cleaned), self.min_observations)

        variance = float(cleaned.var(ddof=1))
        if not isfinite(variance) or variance <= self.variance_tolerance:
            raise InvalidReturnsError("returns are constant or nearly constant")

        messages = []
        if missing_count:
            messages.append(
                f"Dropped {missing_count} NaN return observation(s); values were not forward-filled"
            )
        return cleaned, timestamp, messages

    @staticmethod
    def _slice_as_of(
        returns: pd.Series,
        as_of_date: date | datetime | None,
    ) -> tuple[pd.Series, date]:
        if as_of_date is None:
            return returns.copy(), returns.index[-1].date()
        if not isinstance(as_of_date, date | datetime):
            raise InvalidReturnsError("as_of_date must be a date, datetime, or None")

        cutoff = pd.Timestamp(as_of_date)
        index = returns.index
        if index.tz is not None and cutoff.tzinfo is None:
            cutoff = cutoff.tz_localize(index.tz)
        elif index.tz is None and cutoff.tzinfo is not None:
            raise InvalidReturnsError("as_of_date timezone must match the returns index")
        elif index.tz is not None and cutoff.tzinfo is not None:
            cutoff = cutoff.tz_convert(index.tz)

        return returns.loc[index <= cutoff].copy(), cutoff.date()

    def _realized_volatility(self, returns: pd.Series) -> float:
        realized = float(returns.iloc[-self.realized_window :].std(ddof=1))
        if not isfinite(realized) or realized <= self.variance_tolerance:
            raise InvalidReturnsError(
                f"trailing {self.realized_window}-observation realized volatility "
                "must be positive"
            )
        return realized

    def _build_estimate(
        self,
        *,
        ticker: str,
        timestamp: date,
        cleaned_returns: pd.Series,
        result: Any,
        warnings: list[str],
    ) -> VolatilityEstimate:
        parameters = self._extract_parameters(result.params)
        conditional_volatility = float(result.conditional_volatility.iloc[-1]) / self.RETURN_SCALE
        conditional_variance = conditional_volatility**2

        forecast_variance_scaled = float(
            result.forecast(horizon=1, reindex=False).variance.iloc[-1, 0]
        )
        forecast_volatility = sqrt(forecast_variance_scaled) / self.RETURN_SCALE
        realized_volatility = self._realized_volatility(cleaned_returns)

        if realized_volatility <= 0.0:
            raise InvalidReturnsError("realized volatility must be positive")
        volatility_ratio = conditional_volatility / realized_volatility

        diagnostics = GARCHDiagnostics(
            fit_status=GARCHFitStatus.SUCCESS,
            convergence_status=GARCHConvergenceStatus.CONVERGED,
            observation_count=len(cleaned_returns),
            log_likelihood=self._optional_finite_float(result.loglikelihood),
            warnings=warnings,
        )
        return VolatilityEstimate(
            ticker=ticker,
            timestamp=timestamp,
            conditional_variance=conditional_variance,
            conditional_volatility=conditional_volatility,
            forecast_volatility=forecast_volatility,
            realized_volatility=realized_volatility,
            volatility_ratio=volatility_ratio,
            parameters=parameters,
            diagnostics=diagnostics,
        )

    def _extract_parameters(self, fitted_parameters: Any) -> GARCHParameters:
        return GARCHParameters(
            omega=float(fitted_parameters["omega"]) / (self.RETURN_SCALE**2),
            alpha=float(fitted_parameters["alpha[1]"]),
            gamma=float(fitted_parameters["gamma[1]"]),
            beta=float(fitted_parameters["beta[1]"]),
        )

    @staticmethod
    def _optional_finite_float(value: Any) -> float | None:
        numeric = float(value)
        return numeric if isfinite(numeric) else None

    @staticmethod
    def _fallback_estimate(
        *,
        ticker: str,
        timestamp: date,
        realized_volatility: float,
        observation_count: int,
        convergence_status: GARCHConvergenceStatus,
        warnings: list[str],
        errors: list[str],
        log_likelihood: float | None = None,
    ) -> VolatilityEstimate:
        diagnostics = GARCHDiagnostics(
            fit_status=GARCHFitStatus.FALLBACK,
            convergence_status=convergence_status,
            observation_count=observation_count,
            log_likelihood=log_likelihood,
            warnings=warnings,
            errors=errors,
        )
        return VolatilityEstimate(
            ticker=ticker,
            timestamp=timestamp,
            conditional_variance=realized_volatility**2,
            conditional_volatility=realized_volatility,
            forecast_volatility=realized_volatility,
            realized_volatility=realized_volatility,
            volatility_ratio=1.0,
            parameters=None,
            diagnostics=diagnostics,
        )
