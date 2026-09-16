"""Application-level routes for persisted Phase 3 volatility evaluations."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.db import get_db
from backend.dependencies.market_data import get_market_data_provider
from backend.exceptions import (
    EvaluationNotFoundError,
    InvalidEvaluationError,
    MarketDataUnavailableError,
    PortfolioNotFoundError,
    VolatilityEvaluationNotFoundError,
    VolatilityPersistenceError,
)
from backend.schemas.volatility import (
    MarketRegimeResponse,
    VolatilityEvaluationRequest,
    VolatilityEvaluationResponse,
)
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from quant_engine.data.provider import MarketDataProvider
from quant_engine.regimes.exceptions import (
    InsufficientCoverageError,
    InsufficientStressHistoryError,
    InvalidStressHistoryError,
)
from quant_engine.volatility.exceptions import InsufficientHistoryError, InvalidReturnsError

router = APIRouter(tags=["volatility"])
logger = logging.getLogger("veyra.api")


def _service(db: Session, provider: MarketDataProvider) -> VolatilityEvaluationService:
    return VolatilityEvaluationService(db, provider)


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PortfolioNotFoundError | EvaluationNotFoundError):
        return HTTPException(status_code=404, detail="Portfolio or evaluation not found")
    if isinstance(exc, VolatilityEvaluationNotFoundError):
        return HTTPException(status_code=404, detail="Volatility evaluation not found")
    if isinstance(
        exc,
        InsufficientCoverageError
        | InsufficientStressHistoryError
        | InvalidStressHistoryError
        | InsufficientHistoryError
        | InvalidReturnsError
        | InvalidEvaluationError,
    ):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, MarketDataUnavailableError):
        return HTTPException(status_code=503, detail="Market data is temporarily unavailable")
    if isinstance(exc, VolatilityPersistenceError):
        return HTTPException(status_code=500, detail="Volatility evaluation could not be saved")
    logger.exception("Unexpected volatility evaluation failure")
    return HTTPException(status_code=500, detail="Volatility evaluation failed")


@router.post(
    "/portfolios/{portfolio_id}/volatility/evaluate",
    response_model=VolatilityEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_volatility(
    portfolio_id: str,
    request: VolatilityEvaluationRequest,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    try:
        result = _service(db, provider).evaluate(
            portfolio_id,
            request.as_of_date,
            evaluation_id=request.evaluation_id,
        )
        return VolatilityEvaluationResponse.model_validate(result)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get(
    "/evaluations/{evaluation_id}/volatility",
    response_model=VolatilityEvaluationResponse,
)
def get_evaluation_volatility(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    try:
        result = _service(db, provider).get_evaluation(evaluation_id)
        return VolatilityEvaluationResponse.model_validate(result)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get(
    "/evaluations/{evaluation_id}/regime",
    response_model=MarketRegimeResponse,
)
def get_evaluation_regime(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    try:
        result = _service(db, provider).get_regime(evaluation_id)
        return MarketRegimeResponse.model_validate(result)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/regime/latest",
    response_model=MarketRegimeResponse,
)
def get_latest_portfolio_regime(
    portfolio_id: str,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    try:
        result = _service(db, provider).get_latest_regime(portfolio_id)
        return MarketRegimeResponse.model_validate(result)
    except Exception as exc:
        raise _map_error(exc) from exc
