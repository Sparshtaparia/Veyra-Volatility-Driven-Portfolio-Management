"""
backend/exceptions.py
=====================
Domain and application specific exceptions.
"""


class PortfolioNotFoundError(Exception):
    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio not found: {portfolio_id}")


class EvaluationNotFoundError(Exception):
    def __init__(self, evaluation_id: str):
        self.evaluation_id = evaluation_id
        super().__init__(f"Evaluation not found: {evaluation_id}")


class InvalidPortfolioError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class InvalidEvaluationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class VolatilityEvaluationNotFoundError(Exception):
    def __init__(self, evaluation_id: str):
        self.evaluation_id = evaluation_id
        super().__init__(f"Volatility evaluation not found: {evaluation_id}")


class MarketDataUnavailableError(Exception):
    """Raised when the configured market-data provider cannot serve a request."""


class VolatilityPersistenceError(Exception):
    """Raised when an atomic Phase 3 state write fails."""


class FactorDataUnavailableError(Exception):
    """Raised when the configured Fama-French data source is unavailable."""


class SignalEvaluationNotFoundError(Exception):
    """Raised when an evaluation has no persisted Phase 4 result."""


class SignalPersistenceError(Exception):
    """Raised when the atomic Phase 4 state write fails."""
