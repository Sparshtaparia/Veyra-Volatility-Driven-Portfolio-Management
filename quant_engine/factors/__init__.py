"""Fama-French exposure, normalization, and base-signal components."""

from quant_engine.factors.fama_french import FamaFrenchEstimator
from quant_engine.factors.models import (
    BaseSignal,
    FactorSnapshot,
    FamaFrenchExposure,
    NormalizationMethod,
    SignalConfig,
)
from quant_engine.factors.normalization import normalize_cross_section
from quant_engine.factors.signal import BaseSignalEngine

__all__ = [
    "BaseSignal",
    "BaseSignalEngine",
    "FamaFrenchEstimator",
    "FamaFrenchExposure",
    "FactorSnapshot",
    "NormalizationMethod",
    "SignalConfig",
    "normalize_cross_section",
]
