"""
backend/schemas/portfolio.py
============================
FastAPI schemas for Portfolio API.
"""

from datetime import datetime

from pydantic import BaseModel


class CreatePortfolioRequest(BaseModel):
    name: str
    currency: str = "INR"


class PortfolioResponse(BaseModel):
    portfolio_id: str
    name: str
    currency: str
    created_at: datetime


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
