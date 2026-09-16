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
        if any(value is None for value in (features.rsi, features.macd_histogram, features.atr, features.bollinger_band_width)):
            raise SignalInputError("RSI, MACD histogram, ATR, and Bollinger width are required")
        if features.atr <= 0:
            raise SignalInputError("ATR must be positive when generating a signal")
        if features.bollinger_band_width < 0:
            raise SignalInputError("Bollinger band width must be non-negative")
        rsi = (features.rsi - 50.0) / 50.0
        momentum = tanh(features.macd_histogram / features.atr)
        width_penalty = min(features.bollinger_band_width, 1.0)
        composite = max(-1.0, min(1.0, 0.5 * rsi + 0.5 * momentum))
        direction = SignalDirection.BUY if composite >= self.direction_threshold else SignalDirection.SELL if composite <= -self.direction_threshold else SignalDirection.NEUTRAL
        return BaseSignal(ticker=features.ticker, timestamp=features.timestamp, components=SignalComponents(rsi=rsi, macd_momentum=momentum, band_width_penalty=width_penalty), composite_signal=composite, direction=direction)
