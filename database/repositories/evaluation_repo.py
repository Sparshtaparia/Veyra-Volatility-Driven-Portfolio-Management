"""
database/repositories/evaluation_repo.py
========================================
Persistence layer for Evaluations.

Must NOT contain any quantitative logic or business decisions.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from database.models import EvaluationModel
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_evaluation(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        evaluation_date: date,
        trigger: EvaluationTrigger,
        decision: EvaluationDecision,
        status: EvaluationStatus
    ) -> EvaluationModel:
        db_eval = EvaluationModel(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            evaluation_date=evaluation_date,
            trigger=trigger,
            decision=decision,
            status=status
        )
        self.db.add(db_eval)
        self.db.commit()
        self.db.refresh(db_eval)
        return db_eval

    def get_evaluation(self, evaluation_id: UUID) -> Optional[EvaluationModel]:
        return self.db.execute(
            select(EvaluationModel).where(EvaluationModel.evaluation_id == evaluation_id)
        ).scalar_one_or_none()

    def list_evaluations_for_portfolio(self, portfolio_id: str) -> List[EvaluationModel]:
        return list(self.db.execute(
            select(EvaluationModel).where(EvaluationModel.portfolio_id == portfolio_id)
        ).scalars().all())

    def update_evaluation_status(self, evaluation_id: UUID, status: EvaluationStatus) -> Optional[EvaluationModel]:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation:
            evaluation.status = status
            self.db.commit()
            self.db.refresh(evaluation)
        return evaluation
