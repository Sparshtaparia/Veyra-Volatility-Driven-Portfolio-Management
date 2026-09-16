"""Persistence operations for Phase 5 portfolio control state."""

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    FeedbackUpdateModel,
    PortfolioSnapshotModel,
    PortfolioTargetModel,
    RebalanceEventModel,
    TradeModel,
)
from quant_engine.feedback.models import FeedbackUpdate
from quant_engine.portfolio.models import ExecutedTrade, OptimizationResult


class PortfolioControlRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_targets(
        self, evaluation_id: UUID, portfolio_id: str, result: OptimizationResult
    ) -> list[PortfolioTargetModel]:
        rows = [
            PortfolioTargetModel(
                evaluation_id=evaluation_id,
                portfolio_id=portfolio_id,
                as_of_date=result.as_of_date,
                **target.model_dump(),
                gross_exposure=result.gross_exposure,
                net_exposure=result.net_exposure,
                cash_weight=result.cash_weight,
                expected_volatility=result.expected_volatility,
            )
            for target in result.targets
        ]
        self.db.add_all(rows)
        self.db.flush()
        return rows

    def get_targets(self, evaluation_id: UUID) -> list[PortfolioTargetModel]:
        return list(
            self.db.scalars(
                select(PortfolioTargetModel)
                .where(PortfolioTargetModel.evaluation_id == evaluation_id)
                .order_by(PortfolioTargetModel.ticker)
            ).all()
        )

    def latest_targets(self, portfolio_id: str) -> list[PortfolioTargetModel]:
        latest_date = self.db.scalar(
            select(PortfolioTargetModel.as_of_date)
            .where(PortfolioTargetModel.portfolio_id == portfolio_id)
            .order_by(PortfolioTargetModel.as_of_date.desc())
            .limit(1)
        )
        if latest_date is None:
            return []
        return list(
            self.db.scalars(
                select(PortfolioTargetModel)
                .where(
                    PortfolioTargetModel.portfolio_id == portfolio_id,
                    PortfolioTargetModel.as_of_date == latest_date,
                )
                .order_by(PortfolioTargetModel.ticker)
            ).all()
        )

    def create_rebalance(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        event_date: date,
        portfolio_value: float,
        turnover: float,
        trades: list[ExecutedTrade],
    ) -> RebalanceEventModel:
        event = RebalanceEventModel(
            event_id=uuid4(),
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            event_date=event_date,
            status="SIMULATED",
            portfolio_value=portfolio_value,
            turnover=turnover,
            total_cost=sum(item.transaction_cost + item.slippage_cost for item in trades),
        )
        self.db.add(event)
        self.db.flush()
        self.db.add_all(
            [
                TradeModel(event_id=event.event_id, **trade.model_dump(mode="json"))
                for trade in trades
            ]
        )
        self.db.flush()
        return event

    def get_rebalance(self, evaluation_id: UUID) -> RebalanceEventModel | None:
        return self.db.scalar(
            select(RebalanceEventModel).where(RebalanceEventModel.evaluation_id == evaluation_id)
        )

    def get_trades(self, event_id: UUID) -> list[TradeModel]:
        return list(
            self.db.scalars(select(TradeModel).where(TradeModel.event_id == event_id)).all()
        )

    def create_snapshot(
        self,
        portfolio_id: str,
        evaluation_id: UUID,
        snapshot_date: date,
        portfolio_value: float,
        cash_value: float,
        gross_exposure: float,
        net_exposure: float,
        holdings: list[dict[str, object]],
    ) -> PortfolioSnapshotModel:
        row = PortfolioSnapshotModel(
            portfolio_id=portfolio_id,
            evaluation_id=evaluation_id,
            snapshot_date=snapshot_date,
            portfolio_value=portfolio_value,
            cash_value=cash_value,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            holdings=holdings,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def latest_snapshot(self, portfolio_id: str) -> PortfolioSnapshotModel | None:
        return self.db.scalar(
            select(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshotModel.snapshot_date.desc())
            .limit(1)
        )

    def create_feedback(
        self, evaluation_id: UUID, portfolio_id: str, update: FeedbackUpdate
    ) -> FeedbackUpdateModel:
        row = FeedbackUpdateModel(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            observation_date=update.outcome.observation_date,
            previous_state=update.previous_state.model_dump(mode="json"),
            controlled_signal=update.controlled_signal,
            observed_outcome=update.outcome.model_dump(mode="json"),
            updated_state=update.updated_state.model_dump(mode="json"),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def feedback_history(self, portfolio_id: str) -> list[FeedbackUpdateModel]:
        return list(
            self.db.scalars(
                select(FeedbackUpdateModel)
                .where(FeedbackUpdateModel.portfolio_id == portfolio_id)
                .order_by(FeedbackUpdateModel.observation_date)
            ).all()
        )

    def snapshot_history(self, portfolio_id: str) -> list[PortfolioSnapshotModel]:
        return list(
            self.db.scalars(
                select(PortfolioSnapshotModel)
                .where(PortfolioSnapshotModel.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshotModel.snapshot_date)
            ).all()
        )
