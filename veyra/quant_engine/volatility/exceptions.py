"""Domain exceptions raised by the volatility engine boundary."""


class VolatilityEngineError(Exception):
    """Base class for volatility-engine failures."""


class InvalidReturnsError(VolatilityEngineError):
    """Raised when a return series cannot be used safely."""


class InsufficientHistoryError(InvalidReturnsError):
    """Raised when too few usable observations remain for model fitting."""

    def __init__(self, observation_count: int, minimum_required: int):
        self.observation_count = observation_count
        self.minimum_required = minimum_required
        super().__init__(
            f"GJR-GARCH requires at least {minimum_required} observations; "
            f"received {observation_count}"
        )


class GARCHFitError(VolatilityEngineError):
    """Raised when the third-party GJR-GARCH fit or result extraction fails."""


class GARCHConvergenceError(GARCHFitError):
    """Raised when the optimizer returns a non-zero convergence flag."""
