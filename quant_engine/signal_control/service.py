"""Volatility-conditioned, sign-preserving signal regulation."""
from quant_engine.signal_control.models import RegulatedSignal
from quant_engine.signals.models import BaseSignal, SignalDirection
from quant_engine.volatility.models import MarketRegime


class SignalRegulator:
    """Apply a bounded decay factor; regime never changes signal orientation."""
    minimum_attenuation = 0.20

    def regulate(self, signal: BaseSignal, *, regime: MarketRegime, volatility_ratio: float) -> RegulatedSignal:
        if volatility_ratio < 0:
            raise ValueError("volatility_ratio must be non-negative")
        if regime in (MarketRegime.LOW_VOL, MarketRegime.NORMAL):
            factor = 1.0
        elif regime is MarketRegime.ELEVATED:
            factor = max(0.70, 1.0 / (1.0 + max(0.0, volatility_ratio - 1.0)))
        else:  # HIGH_STRESS is Phase 3's high-volatility regime.
            factor = max(self.minimum_attenuation, 1.0 / (1.0 + 2.0 * max(0.0, volatility_ratio - 1.0)))
        regulated = signal.composite_signal * factor
        direction = SignalDirection.BUY if regulated >= 0.10 else SignalDirection.SELL if regulated <= -0.10 else SignalDirection.NEUTRAL
        return RegulatedSignal(base_signal=signal, regime=regime, volatility_ratio=volatility_ratio, attenuation_factor=factor, regulated_signal=regulated, direction=direction)
