"""
backend/schemas/portfolio.py
============================
FastAPI schemas for Portfolio API.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CreatePortfolioRequest(BaseModel):
    name: str
    currency: str = "INR"

class UpdatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    currency: str = Field(..., min_length=3, max_length=3)
    max_weight_constraint: float = Field(0.40, ge=0.05, le=1.0)


class PortfolioResponse(BaseModel):
    portfolio_id: str
    name: str
    currency: str
    total_value: float
    max_weight_constraint: float
    created_at: datetime
    updated_at: datetime


class AddHoldingRequest(BaseModel):
    ticker: str
    quantity: float
    average_price: float
    current_price: float


class HoldingResponse(BaseModel):
    id: int
    ticker: str
    quantity: float
    average_price: float
    current_price: float
    market_value: float
    weight: float
