from pydantic import BaseModel, Field, model_validator


class AssetOptimizationInput(BaseModel):
    """Input for a single asset into the optimizer."""
    ticker: str
    current_weight: float = Field(ge=0.0, le=1.0)
    expected_signal: float
    volatility: float = Field(ge=0.0)
    composite_risk_score: float = Field(ge=0.0)
    reliability_score: float = Field(ge=0.0)


class OptimizationConstraints(BaseModel):
    """Configurable bounds for the optimizer."""
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    max_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    turnover_limit: float = Field(default=1.0, ge=0.0)
    
    @model_validator(mode="after")
    def validate_bounds(self) -> "OptimizationConstraints":
        if self.min_weight > self.max_weight:
            raise ValueError("min_weight cannot be greater than max_weight")
        return self


class OptimizationOutput(BaseModel):
    """Result of the optimization for a single asset."""
    ticker: str
    target_weight: float = Field(ge=0.0, le=1.0)


class AllocationDelta(BaseModel):
    """Difference between target and current weights for a single asset."""
    ticker: str
    current_weight: float = Field(ge=0.0, le=1.0)
    target_weight: float = Field(ge=0.0, le=1.0)
    delta_weight: float = Field(ge=-1.0, le=1.0)


class AllocationResult(BaseModel):
    """Final result of the allocation step across all assets."""
    allocations: list[AllocationDelta]
    total_turnover: float = Field(ge=0.0)
    decision: str  # "HOLD" or "REBALANCE_REQUIRED"
