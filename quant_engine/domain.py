"""
quant_engine/domain.py
======================
Pure domain contracts for the Veyra portfolio management engine.

These types form the explicit inter-layer contracts. They are:
  - Independent of SQLAlchemy (no ORM imports here)
  - Independent of FastAPI (no request/response decorators)
  - Validated by Pydantic v2

All quantitative layers (signal engine, volatility engine, optimizer, etc.)
will consume and produce subtypes or compositions of these models.

Architecture note
-----------------
This module belongs to the QUANT ENGINE layer. However, the application
services (backend/services/) also use these types to represent portfolio
state, because the domain language is shared.

The separation is:
  - quant_engine/domain.py  → what the domain looks like (types, rules)
  - backend/services/       → orchestration of use cases
  - quant_engine/signals/   → (Phase 2+) signal computation
  - quant_engine/volatility/ → (Phase 3+) GARCH volatility
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


# ==============================================================================
# Enumerations
# ==============================================================================


class EvaluationTrigger(str, Enum):
    """
    What caused this portfolio evaluation to be initiated.

    Phase 1 supports three trigger types.

    Future phases will extend this enum with:
        PERIODIC        - Time-based trigger with configurable cadence
        PORTFOLIO_CHANGE - Triggered by a material change in holdings
        PRICE_THRESHOLD  - Triggered when an asset crosses a price level

    NOTE: Adding new trigger values is a backward-compatible change as long
    as existing consumers handle unknown values gracefully.
    """

    SCHEDULED = "SCHEDULED"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    MANUAL = "MANUAL"


class EvaluationDecision(str, Enum):
    """
    The outcome of a portfolio evaluation cycle.

    HOLD      - The current allocation is acceptable; no trades are required.
    REBALANCE - The current allocation has drifted or a signal change warrants
                adjusting weights. Requires user approval before execution.

    Veyra design principle:
        An evaluation NEVER automatically triggers execution.
        A REBALANCE decision generates a proposal that requires explicit
        user approval before orders are sent to the execution layer.
    """

    HOLD = "HOLD"
    REBALANCE = "REBALANCE"


class EvaluationStatus(str, Enum):
    """
    Lifecycle state of an evaluation record.

    PENDING   - Evaluation has been created; quant pipeline has not yet run.
                In Phase 1, all evaluations remain PENDING because the
                pipeline is not yet implemented.
    COMPLETED - The quant pipeline completed and produced a decision.
    FAILED    - The pipeline encountered an unrecoverable error.
    """

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ==============================================================================
# Portfolio domain models
# ==============================================================================


class PortfolioHolding(BaseModel):
    """
    A single asset position within a portfolio.

    Business rules (enforced here and at DB level):
      - ticker must be non-empty and will be normalized to uppercase
      - weight must be in [0, 1] (fractional allocation)
      - quantity must be non-negative
      - market_value must be non-negative
    """

    ticker: str
    weight: float
    quantity: float
    market_value: float

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("ticker must not be empty")
        return stripped.upper()

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"weight must be >= 0, got {v}")
        if v > 1.0:
            raise ValueError(f"weight must be <= 1, got {v}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"quantity must be >= 0, got {v}")
        return v

    @field_validator("market_value")
    @classmethod
    def validate_market_value(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"market_value must be >= 0, got {v}")
        return v


class Portfolio(BaseModel):
    """
    Complete portfolio state at a point in time.

    Business rules:
      - portfolio_id must not be empty
      - total_value must be non-negative
      - For a non-empty portfolio: sum(weights) must be approximately 1.0
        (tolerance: |sum - 1| <= 1e-6) to account for floating-point arithmetic
      - An empty portfolio (no holdings) is valid — used during creation.
        The weight-sum constraint is only enforced when holdings are present.

    Why allow empty portfolio?
    --------------------------
    When a portfolio is first created it has no holdings. Forcing a weight
    constraint at creation time would make the creation flow awkward. The
    portfolio becomes meaningful (and weight-constrained) once holdings are added.
    """

    portfolio_id: str
    holdings: list[PortfolioHolding]
    total_value: float
    as_of_date: date

    @field_validator("portfolio_id")
    @classmethod
    def validate_portfolio_id(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("portfolio_id must not be empty")
        return stripped

    @field_validator("total_value")
    @classmethod
    def validate_total_value(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"total_value must be >= 0, got {v}")
        return v

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "Portfolio":
        """
        Enforce that weights approximately sum to 1 for non-empty portfolios.

        The tolerance of 1e-6 accommodates floating-point arithmetic when
        weights are computed as market_value / total_value.
        """
        if not self.holdings:
            # Empty portfolio is valid (e.g., newly created)
            return self

        weight_sum = sum(h.weight for h in self.holdings)
        tolerance = 1e-6
        if abs(weight_sum - 1.0) > tolerance:
            raise ValueError(
                f"Portfolio weights must sum to approximately 1.0 "
                f"(tolerance {tolerance}), got {weight_sum:.10f}"
            )
        return self


# ==============================================================================
# Evaluation domain models
# ==============================================================================


class EvaluationRequest(BaseModel):
    """
    Input contract for triggering a portfolio evaluation.

    Passed from the API layer → service layer.
    """

    portfolio_id: str
    evaluation_date: date
    trigger: EvaluationTrigger

    @field_validator("portfolio_id")
    @classmethod
    def validate_portfolio_id(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("portfolio_id must not be empty")
        return stripped


class EvaluationResult(BaseModel):
    """
    Output contract from a completed evaluation cycle.

    evaluation_id is the PRIMARY CORRELATION KEY across all layers.
    It must appear in:
      - Database record (Phase 1)
      - Service logs (Phase 1)
      - API response (Phase 1)
      - Quant engine logs (Phase 2+)
      - Execution layer (Phase 5+)
      - Feedback loop (Phase 7+)

    Never generate a different evaluation_id in different layers.
    Generate ONCE at evaluation creation; propagate everywhere.
    """

    evaluation_id: UUID
    portfolio_id: str
    evaluation_date: date
    trigger: EvaluationTrigger
    decision: EvaluationDecision
    status: EvaluationStatus
    created_at: datetime
