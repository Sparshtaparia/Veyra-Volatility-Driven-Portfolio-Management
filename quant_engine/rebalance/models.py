from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class RebalanceAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class RebalanceOrder(BaseModel):
    ticker: str
    action: RebalanceAction
    current_weight: float = Field(ge=0.0, le=1.0)
    target_weight: float = Field(ge=0.0, le=1.0)
    weight_delta: float = Field(ge=-1.0, le=1.0)
    current_value: float = Field(ge=0.0)
    target_value: float = Field(ge=0.0)
    delta_value: float
    current_price: float = Field(gt=0.0)
    quantity: float = Field(ge=0.0)

class RebalancePlan(BaseModel):
    evaluation_id: UUID
    portfolio_id: str
    orders: List[RebalanceOrder]
    total_turnover: float = Field(ge=0.0)
    valid: bool
    decision: str  # HOLD or REBALANCE_REQUIRED
