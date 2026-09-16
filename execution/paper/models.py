from enum import Enum
from typing import List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"

class PaperOrder(BaseModel):
    ticker: str
    side: str  # "BUY" or "SELL"
    quantity: float = Field(gt=0.0)
    reference_price: float = Field(gt=0.0)
    execution_price: float = Field(gt=0.0)
    gross_notional: float = Field(gt=0.0)
    transaction_cost: float = Field(ge=0.0)
    slippage_cost: float = Field(ge=0.0)
    net_cash_change: float
    status: OrderStatus
    executed_at: datetime
    error_message: str | None = None

class PaperExecutionResult(BaseModel):
    evaluation_id: UUID
    portfolio_id: str
    orders: List[PaperOrder]
    execution_time: datetime
    total_cost: float = Field(ge=0.0)
    simulated_holdings: List[dict]
