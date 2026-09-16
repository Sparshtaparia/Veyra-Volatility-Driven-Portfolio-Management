"""Persistence operations for cross-sectional market regime states."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import RegimeStateModel
from quant_engine.regimes.models import MarketStressSnapshot
from quant_engine.volatility.models import MarketVolatilityState


class RegimeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        state: MarketVolatilityState,
        snapshot: MarketStressSnapshot,
    ) -> RegimeStateModel:
        record = RegimeStateModel(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            as_of_date=state.as_of_date,
            total_asset_count=state.total_asset_count,
            eligible_asset_count=state.eligible_asset_count,
            model_fit_count=state.model_fit_count,
            fallback_count=state.fallback_count,
            failed_asset_count=state.failed_asset_count,
            excluded_count=state.excluded_count,
            aggregate_volatility=state.aggregate_volatility,
            median_realized_volatility=snapshot.median_realized_volatility,
            median_volatility_ratio=state.median_volatility_ratio,
            ratio_iqr=snapshot.volatility_ratio_iqr,
            stress_score=state.stress_score,
            adaptive_threshold=state.adaptive_threshold,
            distance_to_threshold=state.distance_to_threshold,
            regime=state.regime,
            coverage_ratio=state.coverage_ratio,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_evaluation(self, evaluation_id: UUID) -> RegimeStateModel | None:
        return self.db.execute(
            select(RegimeStateModel).where(RegimeStateModel.evaluation_id == evaluation_id)
        ).scalar_one_or_none()

    def get_latest_for_portfolio(self, portfolio_id: str) -> RegimeStateModel | None:
        statement = (
            select(RegimeStateModel)
            .where(RegimeStateModel.portfolio_id == portfolio_id)
            .order_by(RegimeStateModel.as_of_date.desc(), RegimeStateModel.created_at.desc())
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_history_for_portfolio(
        self,
        portfolio_id: str,
        *,
        through_date: date | None = None,
    ) -> list[RegimeStateModel]:
        statement = select(RegimeStateModel).where(
            RegimeStateModel.portfolio_id == portfolio_id
        )
        if through_date is not None:
            statement = statement.where(RegimeStateModel.as_of_date <= through_date)
        statement = statement.order_by(
            RegimeStateModel.as_of_date.asc(), RegimeStateModel.created_at.asc()
        )
        return list(self.db.execute(statement).scalars().all())
