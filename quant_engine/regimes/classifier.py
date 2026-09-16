"""Classification of market stress against quantile-derived boundaries."""

from math import isfinite

from quant_engine.regimes.models import RegimeClassification, ThresholdResult
from quant_engine.volatility.models import MarketRegime


class RegimeClassifier:
    """Map a stress score into one of four deliberately coarse regimes."""

    def classify(
        self,
        stress_score: float,
        thresholds: ThresholdResult,
    ) -> RegimeClassification:
        if not isfinite(stress_score) or stress_score <= 0.0:
            raise ValueError("stress_score must be finite and positive")

        if stress_score >= thresholds.adaptive_threshold:
            regime = MarketRegime.HIGH_STRESS
        elif stress_score > thresholds.center:
            regime = MarketRegime.ELEVATED
        elif stress_score < thresholds.low_boundary:
            regime = MarketRegime.LOW_VOL
        else:
            regime = MarketRegime.NORMAL

        return RegimeClassification(
            regime=regime,
            distance_to_threshold=stress_score - thresholds.adaptive_threshold,
        )
