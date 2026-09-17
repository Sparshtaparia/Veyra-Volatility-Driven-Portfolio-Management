"""Ownership checks based exclusively on the verified Supabase JWT subject."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.dependencies.auth import CurrentUser
from backend.exceptions import PortfolioNotFoundError
from backend.services.portfolio_service import PortfolioService
from database.repositories.evaluation_repo import EvaluationRepository


def require_portfolio_owner(db: Session, portfolio_id: str, user: CurrentUser) -> None:
    try:
        PortfolioService(db).get_portfolio(portfolio_id, user_id=user.user_id)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Portfolio not found") from exc


def require_evaluation_owner(db: Session, evaluation_id: UUID, user: CurrentUser) -> str:
    evaluation = EvaluationRepository(db).get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    require_portfolio_owner(db, evaluation.portfolio_id, user)
    return evaluation.portfolio_id
