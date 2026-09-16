"""Persistence operations for per-asset volatility states."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import VolatilityStateModel
from quant_engine.volatility.models import GARCHFitStatus, VolatilityEstimate


class VolatilityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        estimates: Sequence[VolatilityEstimate],
    ) -> list[VolatilityStateModel]:
        records = []
        for estimate in estimates:
            parameters = estimate.parameters
            record = VolatilityStateModel(
                evaluation_id=evaluation_id,
                portfolio_id=portfolio_id,
                ticker=estimate.ticker,
                as_of_date=estimate.timestamp,
                omega=parameters.omega if parameters else None,
                alpha=parameters.alpha if parameters else None,
                gamma=parameters.gamma if parameters else None,
                beta=parameters.beta if parameters else None,
                persistence=parameters.persistence if parameters else None,
                conditional_variance=estimate.conditional_variance,
                conditional_volatility=estimate.conditional_volatility,
                forecast_volatility=estimate.forecast_volatility,
                realized_volatility=estimate.realized_volatility,
                volatility_ratio=estimate.volatility_ratio,
                fit_status=estimate.diagnostics.fit_status,
                convergence_status=estimate.diagnostics.convergence_status,
                observation_count=estimate.diagnostics.observation_count,
                used_fallback=(
                    estimate.diagnostics.fit_status is GARCHFitStatus.FALLBACK
                ),
            )
            records.append(record)

        self.db.add_all(records)
        self.db.flush()
        return records

    def get_by_evaluation(self, evaluation_id: UUID) -> list[VolatilityStateModel]:
        statement = (
            select(VolatilityStateModel)
            .where(VolatilityStateModel.evaluation_id == evaluation_id)
            .order_by(VolatilityStateModel.ticker)
        )
        return list(self.db.execute(statement).scalars().all())

    def get_latest_for_portfolio(self, portfolio_id: str) -> list[VolatilityStateModel]:
        latest = self.db.execute(
            select(VolatilityStateModel)
            .where(VolatilityStateModel.portfolio_id == portfolio_id)
            .order_by(
                VolatilityStateModel.as_of_date.desc(),
                VolatilityStateModel.created_at.desc(),
            )
            .limit(1)
        ).scalar_one_or_none()
        return self.get_by_evaluation(latest.evaluation_id) if latest else []

    def get_for_ticker(
        self,
        portfolio_id: str,
        ticker: str,
    ) -> list[VolatilityStateModel]:
        statement = (
            select(VolatilityStateModel)
            .where(
                VolatilityStateModel.portfolio_id == portfolio_id,
                VolatilityStateModel.ticker == ticker.strip().upper(),
            )
            .order_by(VolatilityStateModel.as_of_date.asc())
        )
        return list(self.db.execute(statement).scalars().all())
