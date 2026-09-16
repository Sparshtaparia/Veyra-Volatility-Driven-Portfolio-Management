"""Typed contracts for the Phase 3 volatility and market-regime layer."""

from quant_engine.volatility.exceptions import (
    GARCHConvergenceError,
    GARCHFitError,
    InsufficientHistoryError,
    InvalidReturnsError,
    VolatilityEngineError,
)
from quant_engine.volatility.gjr_garch import GJRGarchEngine
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    MarketRegime,
    MarketVolatilityState,
    VolatilityEstimate,
)

__all__ = [
    "GARCHConvergenceError",
    "GARCHConvergenceStatus",
    "GARCHDiagnostics",
    "GARCHFitError",
    "GARCHFitStatus",
    "GARCHParameters",
    "GJRGarchEngine",
    "InsufficientHistoryError",
    "InvalidReturnsError",
    "MarketRegime",
    "MarketVolatilityState",
    "VolatilityEngineError",
    "VolatilityEstimate",
]
