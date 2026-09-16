from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.dependencies.auth import CurrentUser, require_auth
from backend.dependencies.db import get_db
from backend.dependencies.market_data import get_market_data_provider
from backend.services.rebalance_service import RebalanceService
from backend.services.portfolio_service import PortfolioService
from quant_engine.data.provider import MarketDataProvider

router = APIRouter(tags=["rebalance"])

class RebalanceRequest(BaseModel):
    as_of_date: date

@router.post(
    "/portfolios/{portfolio_id}/rebalance",
    status_code=status.HTTP_201_CREATED,
)
def execute_rebalance(
    portfolio_id: str,
    request: RebalanceRequest,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    user: CurrentUser = Depends(require_auth),
):
    # Verify ownership
    portfolio_service = PortfolioService(db)
    try:
        portfolio_service.get_portfolio(portfolio_id, user_id=user.user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")

    service = RebalanceService(db, provider)
    try:
        result = service.execute_paper_rebalance(portfolio_id, request.as_of_date)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Rebalance execution failed")
