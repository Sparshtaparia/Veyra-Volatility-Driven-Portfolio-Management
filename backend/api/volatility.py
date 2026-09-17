"""Application-level routes for persisted Phase 3 volatility evaluations."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.auth import CurrentUser, require_auth
from backend.dependencies.db import get_db
from backend.dependencies.factor_data import get_factor_data_provider
from backend.dependencies.market_data import get_market_data_provider
from backend.dependencies.ownership import require_evaluation_owner, require_portfolio_owner
from backend.exceptions import (
    EvaluationNotFoundError,
    InvalidEvaluationError,
    MarketDataUnavailableError,
    PortfolioNotFoundError,
    VolatilityEvaluationNotFoundError,
    VolatilityPersistenceError,
)
from backend.schemas.signal_control import (
    AssetDecisionResponse,
    SignalDecisionEvaluationRequest,
    SignalDecisionEvaluationResponse,
)
from backend.schemas.signals import SignalEvaluationResponse
from backend.schemas.volatility import (
    MarketRegimeResponse,
    VolatilityEvaluationRequest,
    VolatilityEvaluationResponse,
)
from backend.services.signal_decision_evaluation_service import SignalEvaluationService
from backend.services.volatility_evaluation_service import VolatilityEvaluationService
from quant_engine.data.provider import MarketDataProvider
from quant_engine.factors.provider import FactorDataProvider
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


def _signal_service(db: Session, provider: MarketDataProvider) -> SignalEvaluationService:
    return SignalEvaluationService(db, provider)


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
    "/portfolios/{portfolio_id}/signals/evaluate",
    response_model=SignalDecisionEvaluationResponse | SignalEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_signals(
    portfolio_id: str,
    request: SignalDecisionEvaluationRequest,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    factor_provider: FactorDataProvider = Depends(get_factor_data_provider),
    user: CurrentUser = Depends(require_auth),
):
    require_portfolio_owner(db, portfolio_id, user)
    try:
        try:
            result = _signal_service(db, provider).evaluate(
                portfolio_id,
                request.as_of_date,
                evaluation_id=request.evaluation_id,
            )
        except PortfolioNotFoundError:
            # The persisted Phase 4 endpoint originally owned this route. Keep
            # it as a compatibility fallback while the newer decision flow is
            # available for portfolios using the expanded pipeline.
            from backend.api import signals as legacy_signals

            return legacy_signals._service(db, provider, factor_provider).evaluate(
                portfolio_id,
                request.as_of_date,
                evaluation_id=request.evaluation_id,
            )
        return SignalDecisionEvaluationResponse(
            evaluation_id=result.evaluation_id,
            portfolio_id=result.portfolio_id,
            as_of_date=result.as_of_date,
            composite_risk=result.composite_risk,
            allocation_result=result.allocation_result,
            controls=[AssetDecisionResponse(
                ticker=item.regulated_signal.base_signal.ticker,
                base_signal=item.regulated_signal.base_signal.composite_signal,
                regulated_signal=item.regulated_signal.regulated_signal,
                attenuation_factor=item.regulated_signal.attenuation_factor,
                control_output=item.control_output,
                direction=item.direction,
                decision_state=item.decision_state,
                regime=item.regime,
                volatility_state=item.volatility_state,
                risk_state=item.risk_state,
                reliability_state=item.reliability_state,
                reason_codes=item.reason_codes,
            ) for item in result.controls],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise _map_error(exc) from exc


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
    user: CurrentUser = Depends(require_auth),
):
    require_portfolio_owner(db, portfolio_id, user)
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
    user: CurrentUser = Depends(require_auth),
):
    require_evaluation_owner(db, evaluation_id, user)
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
    user: CurrentUser = Depends(require_auth),
):
    require_evaluation_owner(db, evaluation_id, user)
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
    user: CurrentUser = Depends(require_auth),
):
    require_portfolio_owner(db, portfolio_id, user)
    try:
        result = _service(db, provider).get_latest_regime(portfolio_id)
        return MarketRegimeResponse.model_validate(result)
    except Exception as exc:
        raise _map_error(exc) from exc
