"""Analytics endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.db import get_db
from backend.dependencies.auth import CurrentUser, require_auth
from backend.services.analytics_service import AnalyticsService
from backend.schemas.analytics import AnalyticsDashboardResponse

router = APIRouter(tags=["analytics"])

@router.get("/portfolios/{portfolio_id}/analytics/dashboard", response_model=AnalyticsDashboardResponse)
def get_analytics_dashboard(
    portfolio_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    try:
        service = AnalyticsService(db)
        return service.get_dashboard(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate analytics dashboard")
