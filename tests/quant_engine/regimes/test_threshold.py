"""Tests for rolling and fixed stress thresholds."""

from datetime import date, timedelta

import numpy as np
import pytest

from quant_engine.regimes.exceptions import InsufficientStressHistoryError
from quant_engine.regimes.models import StressObservation
from quant_engine.regimes.threshold import FixedThresholdStrategy, RollingQuantileThreshold

START = date(2026, 1, 1)


def history(scores: list[float]) -> list[StressObservation]:
    return [
        StressObservation(
            timestamp=START + timedelta(days=position),
            stress_score=score,
            eligible_asset_count=10,
            coverage_ratio=1.0,
        )
        for position, score in enumerate(scores)
    ]


def test_rolling_quantiles_use_only_configured_window() -> None:
    observations = history([0.4, 0.6, 0.8, 1.0, 1.2, 1.4])
    strategy = RollingQuantileThreshold(window_length=4, minimum_history=4)

    result = strategy.calculate(observations, observations[-1].timestamp)
    expected = np.asarray([0.8, 1.0, 1.2, 1.4])

    assert result.low_boundary == pytest.approx(np.quantile(expected, 0.25))
    assert result.center == pytest.approx(np.quantile(expected, 0.50))
    assert result.adaptive_threshold == pytest.approx(np.quantile(expected, 0.75))
    assert result.observation_count == 4


def test_threshold_requires_minimum_history() -> None:
    strategy = RollingQuantileThreshold(window_length=5, minimum_history=4)

    with pytest.raises(InsufficientStressHistoryError) as error:
        strategy.calculate(history([0.8, 1.0, 1.2]), START + timedelta(days=2))

    assert error.value.observation_count == 3


def test_threshold_is_deterministic_and_lookahead_safe() -> None:
    baseline = history([0.8, 0.9, 1.0, 1.1, 1.2])
    strategy = RollingQuantileThreshold(window_length=5, minimum_history=5)
    as_of = baseline[-1].timestamp

    first = strategy.calculate(baseline, as_of)
    future = history([0.8, 0.9, 1.0, 1.1, 1.2, 1000.0, 0.001])
    second = strategy.calculate(future, as_of)

    assert second == first


def test_threshold_handles_extreme_historical_values() -> None:
    observations = history([0.001, 0.8, 1.0, 1.2, 1000.0])
    strategy = RollingQuantileThreshold(window_length=5, minimum_history=5)

    result = strategy.calculate(observations, observations[-1].timestamp)

    assert result.low_boundary == pytest.approx(0.8)
    assert result.center == pytest.approx(1.0)
    assert result.adaptive_threshold == pytest.approx(1.2)


def test_fixed_threshold_is_explicit_compatibility_mode() -> None:
    observations = history([0.8, 1.0, 1.2])

    result = FixedThresholdStrategy(1.196).calculate(
        observations,
        observations[-1].timestamp,
    )

    assert result.adaptive_threshold == pytest.approx(1.196)
    assert result.strategy == "fixed_research_compatibility"
