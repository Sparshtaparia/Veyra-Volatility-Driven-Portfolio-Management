"""Domain exceptions for market-stress aggregation and regime classification."""


class RegimeError(Exception):
    """Base class for market-regime failures."""


class InsufficientCoverageError(RegimeError):
    """Raised when too few eligible assets support a market-level result."""

    def __init__(
        self,
        eligible_asset_count: int,
        total_asset_count: int,
        minimum_asset_count: int,
        minimum_coverage_ratio: float,
    ) -> None:
        self.eligible_asset_count = eligible_asset_count
        self.total_asset_count = total_asset_count
        self.minimum_asset_count = minimum_asset_count
        self.minimum_coverage_ratio = minimum_coverage_ratio
        coverage_ratio = (
            eligible_asset_count / total_asset_count if total_asset_count else 0.0
        )
        super().__init__(
            "Insufficient market-volatility coverage: "
            f"{eligible_asset_count}/{total_asset_count} eligible assets "
            f"(coverage={coverage_ratio:.3f}); requires at least "
            f"{minimum_asset_count} assets and coverage={minimum_coverage_ratio:.3f}"
        )


class InsufficientStressHistoryError(RegimeError):
    """Raised when an adaptive threshold lacks enough historical observations."""

    def __init__(self, observation_count: int, minimum_required: int) -> None:
        self.observation_count = observation_count
        self.minimum_required = minimum_required
        super().__init__(
            f"Adaptive threshold requires at least {minimum_required} stress observations; "
            f"received {observation_count}"
        )


class InvalidStressHistoryError(RegimeError):
    """Raised when the historical stress series is malformed."""
