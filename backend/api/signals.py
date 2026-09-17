"""Application endpoints for Phase 4 intelligence outputs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.db import get_db
from backend.dependencies.factor_data import get_factor_data_provider
from backend.dependencies.market_data import get_market_data_provider
from backend.exceptions import (
    FactorDataUnavailableError,
    MarketDataUnavailableError,
    PortfolioNotFoundError,
    SignalEvaluationNotFoundError,
    SignalPersistenceError,
)
from backend.schemas.signals import (
    ExplainabilityResponse,
    SignalEvaluationRequest,
    SignalEvaluationResponse,
)
from backend.services.signal_evaluation_service import SignalEvaluationService
from quant_engine.data.provider import MarketDataProvider
from quant_engine.factors.provider import FactorDataProvider
from quant_engine.regimes.exceptions import RegimeError
from quant_engine.risk.models import RiskState
from quant_engine.volatility.exceptions import VolatilityEngineError

router = APIRouter(tags=["signals"])


def _service(
    db: Session,
    market_provider: MarketDataProvider,
    factor_provider: FactorDataProvider,
) -> SignalEvaluationService:
    return SignalEvaluationService(db, market_provider, factor_provider)


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, PortfolioNotFoundError | SignalEvaluationNotFoundError):
        return HTTPException(status_code=404, detail="Portfolio or signal evaluation not found")
    if isinstance(exc, VolatilityEngineError | RegimeError | ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, MarketDataUnavailableError | FactorDataUnavailableError):
        return HTTPException(
            status_code=503, detail="Required market or factor data is unavailable"
        )
    if isinstance(exc, SignalPersistenceError):
        return HTTPException(status_code=500, detail="Signal evaluation could not be saved")
    return HTTPException(status_code=500, detail="Signal evaluation failed")


@router.post(
    "/portfolios/{portfolio_id}/signals/evaluate",
    response_model=SignalEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_signals(
    portfolio_id: str,
    request: SignalEvaluationRequest,
    db: Session = Depends(get_db),
    market_provider: MarketDataProvider = Depends(get_market_data_provider),
    factor_provider: FactorDataProvider = Depends(get_factor_data_provider),
):
    try:
        from backend.services.portfolio_service import PortfolioService
        portfolio_service = PortfolioService(db)
        portfolio_service.sync_prices(portfolio_id, request.as_of_date, market_provider)
        
        result = _service(db, market_provider, factor_provider).evaluate(
            portfolio_id, request.as_of_date, evaluation_id=request.evaluation_id
        )
        return SignalEvaluationResponse.model_validate(result)
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/evaluations/{evaluation_id}/signals", response_model=SignalEvaluationResponse)
def get_signals(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    market_provider: MarketDataProvider = Depends(get_market_data_provider),
    factor_provider: FactorDataProvider = Depends(get_factor_data_provider),
):
    try:
        return SignalEvaluationResponse.model_validate(
            _service(db, market_provider, factor_provider).get_evaluation(evaluation_id)
        )
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/evaluations/{evaluation_id}/risk", response_model=RiskState)
def get_risk(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    market_provider: MarketDataProvider = Depends(get_market_data_provider),
    factor_provider: FactorDataProvider = Depends(get_factor_data_provider),
):
    try:
        return _service(db, market_provider, factor_provider).get_risk(evaluation_id)
    except Exception as exc:
        raise _error(exc) from exc


@router.get(
    "/evaluations/{evaluation_id}/explainability",
    response_model=ExplainabilityResponse,
)
def get_explainability(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    market_provider: MarketDataProvider = Depends(get_market_data_provider),
    factor_provider: FactorDataProvider = Depends(get_factor_data_provider),
):
    try:
        items = _service(db, market_provider, factor_provider).get_explainability(evaluation_id)
        return ExplainabilityResponse(evaluation_id=evaluation_id, items=items)
    except Exception as exc:
        raise _error(exc) from exc
