"""Tests for four-state market-regime classification."""

from datetime import date

import pytest

from quant_engine.regimes.classifier import RegimeClassifier
from quant_engine.regimes.models import ThresholdResult
from quant_engine.volatility.models import MarketRegime


@pytest.fixture
def thresholds() -> ThresholdResult:
    return ThresholdResult(
        timestamp=date(2026, 9, 16),
        low_boundary=0.8,
        center=1.0,
        adaptive_threshold=1.2,
        observation_count=63,
        window_length=63,
        strategy="rolling_quantile",
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.7, MarketRegime.LOW_VOL),
        (0.8, MarketRegime.NORMAL),
        (1.0, MarketRegime.NORMAL),
        (1.01, MarketRegime.ELEVATED),
        (1.199, MarketRegime.ELEVATED),
        (1.2, MarketRegime.HIGH_STRESS),
        (1.5, MarketRegime.HIGH_STRESS),
    ],
)
def test_classifier_regimes_and_boundaries(
    score: float,
    expected: MarketRegime,
    thresholds: ThresholdResult,
) -> None:
    result = RegimeClassifier().classify(score, thresholds)

    assert result.regime is expected
    assert result.distance_to_threshold == pytest.approx(score - 1.2)
