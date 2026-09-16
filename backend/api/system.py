"""Read-only operational status endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies.db import get_db
from backend.dependencies.market_data import get_market_data_provider
from backend.operations.health import database_readiness
from backend.operations.market_data import ResilientMarketDataProvider
from backend.operations.metrics import metrics
from backend.operations.scheduler import scheduler_service
from backend.schemas.system import RecentRunResponse, SystemStatusResponse
from config.settings import get_settings
from database.repositories.scheduled_run_repo import ScheduledRunRepository

router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status(
    db: Session = Depends(get_db),
    provider: ResilientMarketDataProvider = Depends(get_market_data_provider),
) -> SystemStatusResponse:
    repository = ScheduledRunRepository(db)
    recent = repository.recent()
    return SystemStatusResponse(
        environment=get_settings().app_env,
        database=database_readiness(db),
        scheduler=scheduler_service.status(),
        market_data={
            "provider": provider.name,
            "cache": provider.cache_stats(),
            "last_successful_providers": provider.provider_provenance(),
        },
        scheduled_run_counts=repository.counts_by_status(),
        recent_runs=[
            RecentRunResponse.model_validate(item, from_attributes=True) for item in recent
        ],
        metrics=metrics.snapshot(),
    )
