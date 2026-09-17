"""Interpretable base signals from Phase 2 feature snapshots."""
from math import tanh

from quant_engine.features.models import FeatureSnapshot
from quant_engine.signals.models import BaseSignal, SignalComponents, SignalDirection


class SignalInputError(ValueError):
    pass


class SignalService:
    """Produces a bounded, deterministic technical signal without ML fitting."""

    direction_threshold = 0.10

    def generate(self, features: FeatureSnapshot) -> BaseSignal:
        rsi_value = features.rsi
        macd_value = features.macd_histogram
        atr_value = features.atr
        width_value = features.bollinger_band_width
        if None in (rsi_value, macd_value, atr_value, width_value):
            raise SignalInputError("RSI, MACD histogram, ATR, and Bollinger width are required")
        assert rsi_value is not None
        assert macd_value is not None
        assert atr_value is not None
        assert width_value is not None
        if atr_value <= 0:
            raise SignalInputError("ATR must be positive when generating a signal")
        if width_value < 0:
            raise SignalInputError("Bollinger band width must be non-negative")
        rsi = (rsi_value - 50.0) / 50.0
        momentum = tanh(macd_value / atr_value)
        width_penalty = min(width_value, 1.0)
        composite = max(-1.0, min(1.0, 0.5 * rsi + 0.5 * momentum))
        direction = SignalDirection.BUY if composite >= self.direction_threshold else SignalDirection.SELL if composite <= -self.direction_threshold else SignalDirection.NEUTRAL
        return BaseSignal(ticker=features.ticker, timestamp=features.timestamp, components=SignalComponents(rsi=rsi, macd_momentum=momentum, band_width_penalty=width_penalty), composite_signal=composite, direction=direction)
