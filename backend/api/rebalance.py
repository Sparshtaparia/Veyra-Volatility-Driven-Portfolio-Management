from datetime import date
from typing import Optional
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


class FeedbackResponse(BaseModel):
    portfolio_id: str
    previous_threshold: float
    observed_volatility: float
    feedback_error: float
    updated_threshold: float
    timestamp: date


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
    except Exception:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")

    service = RebalanceService(db, provider)
    try:
        result = service.execute_paper_rebalance(portfolio_id, request.as_of_date)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Rebalance execution failed")


@router.get(
    "/portfolios/{portfolio_id}/feedback",
    response_model=Optional[FeedbackResponse],
)
def get_feedback(
    portfolio_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """
    Return the latest adaptive-threshold feedback cycle for a portfolio.
    Returns null/204 when no feedback has been generated yet (before first paper rebalance).

    Security: portfolio ownership is verified against the authenticated user.
    """
    from database.models import FeedbackUpdateModel

    # Verify ownership
    portfolio_service = PortfolioService(db)
    try:
        portfolio_service.get_portfolio(portfolio_id, user_id=user.user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")

    latest = (
        db.query(FeedbackUpdateModel)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(FeedbackUpdateModel.observation_date.desc())
        .first()
    )

    if latest is None:
        # No feedback yet — return 204 with no body
        from fastapi import Response
        return Response(status_code=204)

    return FeedbackResponse(
        portfolio_id=portfolio_id,
        previous_threshold=float(latest.previous_state.get("adaptive_threshold", 0.0)),
        observed_volatility=float(latest.observed_outcome.get("observed_volatility", 0.0)),
        feedback_error=float(latest.observed_outcome.get("feedback_error", 0.0)),
        updated_threshold=float(latest.updated_state.get("adaptive_threshold", 0.0)),
        timestamp=latest.observation_date,
    )
