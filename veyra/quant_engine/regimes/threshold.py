"""Adaptive and research-compatibility market-stress thresholds."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from math import isfinite
from typing import Protocol

import numpy as np

from quant_engine.regimes.exceptions import (
    InsufficientStressHistoryError,
    InvalidStressHistoryError,
)
from quant_engine.regimes.models import StressObservation, ThresholdResult


class ThresholdStrategy(Protocol):
    def calculate(
        self,
        history: Sequence[StressObservation],
        as_of_date: date,
    ) -> ThresholdResult: ...


def _historical_window(
    history: Sequence[StressObservation],
    as_of_date: date,
    *,
    window_length: int,
    minimum_history: int,
) -> list[StressObservation]:
    available = [observation for observation in history if observation.timestamp <= as_of_date]
    timestamps = [observation.timestamp for observation in available]
    if timestamps != sorted(timestamps):
        raise InvalidStressHistoryError("stress history must be chronological")
    if len(set(timestamps)) != len(timestamps):
        raise InvalidStressHistoryError("stress history must not contain duplicate timestamps")
    if any(not isfinite(observation.stress_score) for observation in available):
        raise InvalidStressHistoryError("stress history must contain finite scores")
    if len(available) < minimum_history:
        raise InsufficientStressHistoryError(len(available), minimum_history)
    return available[-window_length:]


class RollingQuantileThreshold:
    """Time-varying quantile boundaries over a trailing stress window."""

    def __init__(
        self,
        window_length: int = 63,
        high_quantile: float = 0.75,
        minimum_history: int = 21,
        *,
        low_quantile: float = 0.25,
        center_quantile: float = 0.50,
    ) -> None:
        if window_length < 1:
            raise ValueError("window_length must be positive")
        if not 1 <= minimum_history <= window_length:
            raise ValueError("minimum_history must be between 1 and window_length")
        if not 0.0 <= low_quantile < center_quantile < high_quantile <= 1.0:
            raise ValueError("quantiles must satisfy 0 <= low < center < high <= 1")
        self.window_length = window_length
        self.high_quantile = high_quantile
        self.minimum_history = minimum_history
        self.low_quantile = low_quantile
        self.center_quantile = center_quantile

    def calculate(
        self,
        history: Sequence[StressObservation],
        as_of_date: date,
    ) -> ThresholdResult:
        window = _historical_window(
            history,
            as_of_date,
            window_length=self.window_length,
            minimum_history=self.minimum_history,
        )
        scores = np.asarray([observation.stress_score for observation in window])
        return ThresholdResult(
            timestamp=as_of_date,
            low_boundary=float(np.quantile(scores, self.low_quantile)),
            center=float(np.quantile(scores, self.center_quantile)),
            adaptive_threshold=float(np.quantile(scores, self.high_quantile)),
            observation_count=len(window),
            window_length=self.window_length,
            strategy="rolling_quantile",
        )


class FixedThresholdStrategy:
    """Explicit compatibility strategy for a configured research threshold."""

    def __init__(
        self,
        threshold: float,
        *,
        minimum_history: int = 1,
        low_quantile: float = 0.25,
        center_quantile: float = 0.50,
    ) -> None:
        if not isfinite(threshold) or threshold <= 0.0:
            raise ValueError("threshold must be finite and positive")
        if minimum_history < 1:
            raise ValueError("minimum_history must be positive")
        if not 0.0 <= low_quantile < center_quantile <= 1.0:
            raise ValueError("quantiles must satisfy 0 <= low < center <= 1")
        self.threshold = threshold
        self.minimum_history = minimum_history
        self.low_quantile = low_quantile
        self.center_quantile = center_quantile

    def calculate(
        self,
        history: Sequence[StressObservation],
        as_of_date: date,
    ) -> ThresholdResult:
        window = _historical_window(
            history,
            as_of_date,
            window_length=max(len(history), 1),
            minimum_history=self.minimum_history,
        )
        scores = np.asarray([observation.stress_score for observation in window])
        low_boundary = min(float(np.quantile(scores, self.low_quantile)), self.threshold)
        center = min(float(np.quantile(scores, self.center_quantile)), self.threshold)
        return ThresholdResult(
            timestamp=as_of_date,
            low_boundary=low_boundary,
            center=max(low_boundary, center),
            adaptive_threshold=self.threshold,
            observation_count=len(window),
            window_length=len(window),
            strategy="fixed_research_compatibility",
        )
