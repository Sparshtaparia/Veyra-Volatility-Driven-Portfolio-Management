"""Persistence operations for backtest returns, metrics, and attribution."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import BacktestMetricModel, BacktestModel, BacktestReturnModel
from quant_engine.backtest.models import BacktestResult


class BacktestRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        result: BacktestResult,
        *,
        portfolio_id: str | None,
        variant: str,
        configuration: dict[str, object],
    ) -> UUID:
        backtest_id = uuid4()
        self.db.add(
            BacktestModel(
                backtest_id=backtest_id,
                portfolio_id=portfolio_id,
                name=result.name,
                variant=variant,
                start_date=result.start_date,
                end_date=result.end_date,
                status="COMPLETED",
                configuration=configuration,
            )
        )
        self.db.flush()
        self.db.add_all(
            [
                BacktestReturnModel(backtest_id=backtest_id, **item.model_dump())
                for item in result.returns
            ]
        )
        self.db.add(
            BacktestMetricModel(
                backtest_id=backtest_id,
                **result.metrics.model_dump(),
                attribution=[item.model_dump(mode="json") for item in result.attribution],
            )
        )
        self.db.flush()
        return backtest_id

    def get(self, backtest_id: UUID) -> BacktestModel | None:
        return self.db.scalar(select(BacktestModel).where(BacktestModel.backtest_id == backtest_id))

    def get_returns(self, backtest_id: UUID) -> list[BacktestReturnModel]:
        return list(
            self.db.scalars(
                select(BacktestReturnModel)
                .where(BacktestReturnModel.backtest_id == backtest_id)
                .order_by(BacktestReturnModel.return_realization_date)
            ).all()
        )

    def get_metrics(self, backtest_id: UUID) -> BacktestMetricModel | None:
        return self.db.scalar(
            select(BacktestMetricModel).where(BacktestMetricModel.backtest_id == backtest_id)
        )
