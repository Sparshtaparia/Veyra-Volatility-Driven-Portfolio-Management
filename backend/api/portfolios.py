"""
backend/api/portfolios.py
=========================
FastAPI routes for Portfolios and Evaluations.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.db import get_db
from backend.exceptions import (
    EvaluationNotFoundError,
    InvalidPortfolioError,
    PortfolioNotFoundError,
)
from backend.schemas.evaluation import EvaluatePortfolioRequest, EvaluationResponse
from backend.schemas.portfolio import (
    AddHoldingRequest,
    CreatePortfolioRequest,
    HoldingResponse,
    PortfolioDetailResponse,
    PortfolioResponse,
)
from backend.services.evaluation_service import EvaluationService
from backend.services.portfolio_service import PortfolioService
from quant_engine.domain import EvaluationRequest

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(request: CreatePortfolioRequest, db: Session = Depends(get_db)):
    service = PortfolioService(db)
    portfolio = service.create_portfolio(name=request.name, currency=request.currency)
    return PortfolioResponse(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        currency=portfolio.currency,
        created_at=portfolio.created_at,
    )


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    service = PortfolioService(db)
    try:
        portfolio = service.get_portfolio(portfolio_id)
        return PortfolioDetailResponse(
            portfolio_id=portfolio.id,
            name=portfolio.name,
            currency=portfolio.currency,
            total_value=portfolio.total_value,
            created_at=portfolio.created_at,
        )
    except PortfolioNotFoundError:
        raise HTTPException(status_code=404, detail="Portfolio not found")


@router.get("/{portfolio_id}/holdings", response_model=List[HoldingResponse])
def get_holdings(portfolio_id: str, db: Session = Depends(get_db)):
    service = PortfolioService(db)
    try:
        service.get_portfolio(portfolio_id)
        return [
            HoldingResponse(
                id=holding.id,
                ticker=holding.ticker,
                quantity=holding.quantity,
                average_price=holding.average_price,
                current_price=holding.current_price,
                market_value=holding.market_value,
                weight=holding.weight,
            )
            for holding in service.repo.get_holdings(portfolio_id)
        ]
    except PortfolioNotFoundError:
        raise HTTPException(status_code=404, detail="Portfolio not found")


@router.post("/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
def add_holding(portfolio_id: str, request: AddHoldingRequest, db: Session = Depends(get_db)):
    service = PortfolioService(db)
    try:
        holding = service.add_holding(
            portfolio_id=portfolio_id,
            ticker=request.ticker,
            quantity=request.quantity,
            average_price=request.average_price,
            current_price=request.current_price,
        )
        return HoldingResponse(
            id=holding.id,
            ticker=holding.ticker,
            quantity=holding.quantity,
            average_price=holding.average_price,
            current_price=holding.current_price,
            market_value=holding.market_value,
            weight=holding.weight,
        )
    except PortfolioNotFoundError:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except InvalidPortfolioError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{portfolio_id}/evaluate", response_model=EvaluationResponse, status_code=status.HTTP_202_ACCEPTED)
def evaluate_portfolio(portfolio_id: str, request: EvaluatePortfolioRequest, db: Session = Depends(get_db)):
    service = EvaluationService(db)
    try:
        domain_request = EvaluationRequest(
            portfolio_id=portfolio_id,
            evaluation_date=request.evaluation_date,
            trigger=request.trigger,
        )
        result = service.evaluate_portfolio(portfolio_id=portfolio_id, request=domain_request)
        
        return EvaluationResponse(
            evaluation_id=result.evaluation_id,
            portfolio_id=result.portfolio_id,
            evaluation_date=result.evaluation_date,
            trigger=result.trigger,
            decision=result.decision,
            status=result.status,
            created_at=result.created_at,
        )
    except PortfolioNotFoundError:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{portfolio_id}/evaluations/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(portfolio_id: str, evaluation_id: str, db: Session = Depends(get_db)):
    service = EvaluationService(db)
    try:
        result = service.get_evaluation(evaluation_id=evaluation_id)
        if result.portfolio_id != portfolio_id:
             raise HTTPException(status_code=404, detail="Evaluation not found for this portfolio")
        
        return EvaluationResponse(
            evaluation_id=result.evaluation_id,
            portfolio_id=result.portfolio_id,
            evaluation_date=result.evaluation_date,
            trigger=result.trigger,
            decision=result.decision,
            status=result.status,
            created_at=result.created_at,
        )
    except EvaluationNotFoundError:
        raise HTTPException(status_code=404, detail="Evaluation not found")
