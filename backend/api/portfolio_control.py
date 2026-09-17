"""Phase 5 portfolio upload, paper-control, feedback, and backtest endpoints."""

from datetime import date
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.dependencies.auth import CurrentUser, require_admin, require_auth
from backend.dependencies.db import get_db
from backend.dependencies.market_data import get_market_data_provider
from backend.dependencies.ownership import require_evaluation_owner, require_portfolio_owner
from backend.schemas.portfolio_control import (
    AblationItemResponse,
    AblationRunRequest,
    AblationRunResponse,
    BacktestDetailResponse,
    BacktestRunRequest,
    BacktestRunResponse,
    FeedbackHistoryItem,
    FeedbackRequest,
    ManualPortfolioRequest,
    PortfolioControlRequest,
    PortfolioControlResponse,
    PortfolioUploadResponse,
    UploadedHoldingResponse,
)
from backend.services.backtest_service import BacktestService
from backend.services.portfolio_control_service import PortfolioControlService
from backend.services.portfolio_upload_service import PortfolioUploadService, UploadedHolding
from database.repositories.backtest_repo import BacktestRepository
from database.repositories.portfolio_control_repo import PortfolioControlRepository
from quant_engine.backtest.models import AblationVariant
from quant_engine.data.provider import MarketDataProvider
from quant_engine.feedback.models import FeedbackUpdate

router = APIRouter(tags=["portfolio-control"])


def _upload_response(service: PortfolioUploadService, portfolio) -> PortfolioUploadResponse:
    holdings = service.portfolios.repo.get_holdings(portfolio.id)
    return PortfolioUploadResponse(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        currency=portfolio.currency,
        total_value=portfolio.total_value,
        holdings=[UploadedHoldingResponse.model_validate(item) for item in holdings],
    )


@router.get("/portfolios/{portfolio_id}/holdings", response_model=PortfolioUploadResponse)
def get_portfolio_holdings(
    portfolio_id: str,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    user: CurrentUser = Depends(require_auth),
):
    service = PortfolioUploadService(db, provider)
    portfolio = service.portfolios.get_portfolio(portfolio_id, user_id=user.user_id)
    return _upload_response(service, portfolio)


@router.post("/portfolios/upload", response_model=PortfolioUploadResponse, status_code=201)
async def upload_portfolio(
    name: str = Form(...),
    currency: str = Form("USD"),
    as_of_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    user: CurrentUser = Depends(require_auth),
):
    service = PortfolioUploadService(db, provider)
    try:
        holdings = service.parse(await file.read(), file.filename or "")
        return _upload_response(
            service,
            service.create_portfolio(name, currency, holdings, as_of_date, user.user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/portfolios/manual", response_model=PortfolioUploadResponse, status_code=201)
def create_manual_portfolio(
    request: ManualPortfolioRequest,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    user: CurrentUser = Depends(require_auth),
):
    service = PortfolioUploadService(db, provider)
    try:
        holdings = [UploadedHolding.model_validate(item.model_dump()) for item in request.holdings]
        portfolio = service.create_portfolio(
            request.name, request.currency, holdings, request.as_of_date, user.user_id
        )
        return _upload_response(service, portfolio)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/portfolios/{portfolio_id}/optimize",
    response_model=PortfolioControlResponse,
    status_code=201,
)
def optimize_portfolio(
    portfolio_id: str,
    request: PortfolioControlRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    require_portfolio_owner(db, portfolio_id, user)
    try:
        result = PortfolioControlService(db).optimize_and_rebalance(
            portfolio_id,
            request.evaluation_id,
            sectors=request.sectors,
            exposure_config=request.exposure_config,
            optimizer_config=request.optimizer_config,
            transaction_cost_bps=request.transaction_cost_bps,
            slippage_bps=request.slippage_bps,
        )
        return PortfolioControlResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/portfolios/{portfolio_id}/feedback", response_model=FeedbackUpdate)
def apply_feedback(
    portfolio_id: str,
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    require_portfolio_owner(db, portfolio_id, user)
    try:
        return PortfolioControlService(db).apply_feedback(
            portfolio_id, request.evaluation_id, request.outcome
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _frames(request: BacktestRunRequest):
    returns = pd.DataFrame(request.asset_returns, index=pd.to_datetime(request.return_dates))
    weights = pd.DataFrame(request.target_weights, index=pd.to_datetime(request.signal_dates))
    benchmark = pd.Series(request.benchmark_returns, index=pd.to_datetime(request.return_dates))
    return returns, weights, benchmark


@router.post("/backtests", response_model=BacktestRunResponse, status_code=201)
def run_backtest(
    request: BacktestRunRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_admin),
):
    try:
        returns, weights, benchmark = _frames(request)
        backtest_id, result = BacktestService(db).run(
            request.name,
            returns,
            weights,
            benchmark,
            portfolio_id=request.portfolio_id,
        )
        return BacktestRunResponse(backtest_id=backtest_id, result=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/backtests/ablation", response_model=AblationRunResponse, status_code=201)
def run_ablation(
    request: AblationRunRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_admin),
):
    try:
        returns = pd.DataFrame(request.asset_returns, index=pd.to_datetime(request.return_dates))
        benchmark = pd.Series(request.benchmark_returns, index=pd.to_datetime(request.return_dates))
        weights = {
            AblationVariant(name): pd.DataFrame(values, index=pd.to_datetime(request.signal_dates))
            for name, values in request.variant_weights.items()
        }
        results = BacktestService(db).run_ablation(
            returns, benchmark, weights, portfolio_id=request.portfolio_id
        )
        return AblationRunResponse(
            variants={
                variant.value: AblationItemResponse(backtest_id=item[0], result=item[1])
                for variant, item in results.items()
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/evaluations/{evaluation_id}/portfolio-control", response_model=PortfolioControlResponse
)
def get_portfolio_control(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    require_evaluation_owner(db, evaluation_id, user)
    repository = PortfolioControlRepository(db)
    event = repository.get_rebalance(evaluation_id)
    if event is None:
        raise HTTPException(status_code=404, detail="portfolio control result not found")
    return PortfolioControlResponse.model_validate(
        PortfolioControlService(db).get_portfolio_control(evaluation_id, event.portfolio_id)
    )


@router.get(
    "/portfolios/{portfolio_id}/feedback/history",
    response_model=list[FeedbackHistoryItem],
)
def get_feedback_history(
    portfolio_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    require_portfolio_owner(db, portfolio_id, user)
    return [
        FeedbackHistoryItem.model_validate(item)
        for item in PortfolioControlRepository(db).feedback_history(portfolio_id)
    ]


@router.get("/backtests/{backtest_id}", response_model=BacktestDetailResponse)
def get_backtest(
    backtest_id: UUID,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_admin),
):
    repository = BacktestRepository(db)
    metadata = repository.get(backtest_id)
    metrics = repository.get_metrics(backtest_id)
    if metadata is None or metrics is None:
        raise HTTPException(status_code=404, detail="backtest not found")
    metric_values = {
        key: getattr(metrics, key)
        for key in (
            "total_return",
            "cagr",
            "sharpe",
            "sortino",
            "calmar",
            "max_drawdown",
            "volatility",
            "win_rate",
            "turnover",
            "alpha",
            "beta",
            "attribution",
        )
    }
    return BacktestDetailResponse(
        backtest_id=metadata.backtest_id,
        portfolio_id=metadata.portfolio_id,
        name=metadata.name,
        variant=metadata.variant,
        start_date=metadata.start_date,
        end_date=metadata.end_date,
        status=metadata.status,
        configuration=metadata.configuration,
        returns=[
            {
                key: getattr(item, key)
                for key in (
                    "signal_date",
                    "rebalance_date",
                    "execution_date",
                    "return_realization_date",
                    "gross_return",
                    "net_return",
                    "benchmark_return",
                    "turnover",
                    "transaction_cost",
                )
            }
            for item in repository.get_returns(backtest_id)
        ],
        metrics=metric_values,
    )
