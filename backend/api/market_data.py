"""
backend/api/market_data.py
==========================
API endpoints for Market Data and Features.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.dependencies.auth import CurrentUser, require_auth
from backend.dependencies.db import get_db
from backend.dependencies.market_data import get_market_data_provider
from backend.exceptions import PortfolioNotFoundError
from backend.services.portfolio_service import PortfolioService
from quant_engine.data.provider import MarketDataProvider
from quant_engine.features.models import FeatureSnapshot
from quant_engine.features.service import FeatureService

router = APIRouter(prefix="/portfolios/{portfolio_id}/features", tags=["market_data"])


@router.get("", response_model=list[FeatureSnapshot])
def get_portfolio_features(
    portfolio_id: str,
    ticker: str,
    start_date: date = Query(..., description="Start date for feature calculation"),
    end_date: date = Query(..., description="End date for feature calculation"),
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    user: CurrentUser = Depends(require_auth),
):
    """
    Orchestration endpoint:
    Fetches raw market data, computes technical features safely, and returns the snapshots.
    Validates that the ticker belongs to the portfolio.
    """
    portfolio_service = PortfolioService(db)
    try:
        portfolio_service.get_portfolio(portfolio_id, user_id=user.user_id)

        # Validate that ticker is actually in the portfolio
        holdings = portfolio_service.repo.get_holdings(portfolio_id)
        holding_tickers = [h.ticker for h in holdings]
        if ticker.upper() not in holding_tickers:
            raise HTTPException(
                status_code=404, detail=f"Ticker {ticker} not found in portfolio {portfolio_id}"
            )

        feature_service = FeatureService(provider=provider)

        try:
            snapshots = feature_service.generate_features(ticker, start_date, end_date)
            return snapshots
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))

    except PortfolioNotFoundError:
        raise HTTPException(status_code=404, detail="Portfolio not found")
