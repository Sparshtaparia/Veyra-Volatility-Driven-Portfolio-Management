"""
backend/services/evaluation_service.py
======================================
Business logic for Evaluations.
"""

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.exceptions import EvaluationNotFoundError, PortfolioNotFoundError
from backend.services.portfolio_service import PortfolioService
from database.repositories.evaluation_repo import EvaluationRepository
from quant_engine.domain import (
    EvaluationDecision,
    EvaluationRequest,
    EvaluationResult,
    EvaluationStatus,
)


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EvaluationRepository(db)
        self.portfolio_service = PortfolioService(db)

    def evaluate_portfolio(self, portfolio_id: str, request: EvaluationRequest) -> EvaluationResult:
        # STEP 1: Load portfolio
        portfolio_model = self.portfolio_service.get_portfolio(portfolio_id)
        if not portfolio_model:
            raise PortfolioNotFoundError(portfolio_id)

        # STEP 2: Convert to domain
        self.portfolio_service.to_domain(portfolio_id, request.evaluation_date)

        # STEP 3: Generate evaluation_id
        evaluation_id = uuid4()

        # STEP 4: Create EvaluationModel
        # This is a stub. Future phases will plug in Quant Engine here.
        status = EvaluationStatus.PENDING
        decision = EvaluationDecision.HOLD

        # STEP 5: Persist evaluation
        db_eval = self.repo.create_evaluation(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            evaluation_date=request.evaluation_date,
            trigger=request.trigger,
            decision=decision,
            status=status,
        )

        # STEP 6: Return EvaluationResult
        return EvaluationResult(
            evaluation_id=db_eval.evaluation_id,
            portfolio_id=db_eval.portfolio_id,
            evaluation_date=db_eval.evaluation_date,
            trigger=db_eval.trigger,
            decision=db_eval.decision,
            status=db_eval.status,
            created_at=db_eval.created_at,
        )

    def get_evaluation(self, evaluation_id: str) -> EvaluationResult:
        try:
            eval_uuid = UUID(hex=evaluation_id) if isinstance(evaluation_id, str) else evaluation_id
        except ValueError:
            raise EvaluationNotFoundError(evaluation_id)

        db_eval = self.repo.get_evaluation(eval_uuid)
        if not db_eval:
            raise EvaluationNotFoundError(evaluation_id)

        return EvaluationResult(
            evaluation_id=db_eval.evaluation_id,
            portfolio_id=db_eval.portfolio_id,
            evaluation_date=db_eval.evaluation_date,
            trigger=db_eval.trigger,
            decision=db_eval.decision,
            status=db_eval.status,
            created_at=db_eval.created_at,
        )

    def list_evaluations(self, portfolio_id: str) -> list[EvaluationResult]:
        self.portfolio_service.get_portfolio(portfolio_id)
        return [
            EvaluationResult(
                evaluation_id=item.evaluation_id,
                portfolio_id=item.portfolio_id,
                evaluation_date=item.evaluation_date,
                trigger=item.trigger,
                decision=item.decision,
                status=item.status,
                created_at=item.created_at,
            )
            for item in self.repo.list_evaluations_for_portfolio(portfolio_id)
        ]
