"""Application service for persisted chronological backtests and ablations."""

from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from database.repositories.backtest_repo import BacktestRepository
from quant_engine.backtest.ablation import AblationRunner
from quant_engine.backtest.engine import BacktestEngine
from quant_engine.backtest.models import AblationVariant, BacktestResult


class BacktestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.engine = BacktestEngine()
        self.ablation = AblationRunner(self.engine)
        self.repository = BacktestRepository(db)

    def run(
        self,
        name: str,
        asset_returns: pd.DataFrame,
        target_weights: pd.DataFrame,
        benchmark_returns: pd.Series,
        *,
        portfolio_id: str | None = None,
        variant: str = AblationVariant.FULL_STATE_COUPLED.value,
    ) -> tuple[UUID, BacktestResult]:
        result = self.engine.run(name, asset_returns, target_weights, benchmark_returns)
        try:
            backtest_id = self.repository.create(
                result,
                portfolio_id=portfolio_id,
                variant=variant,
                configuration=self.engine.config.model_dump(mode="json"),
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return backtest_id, result

    def run_ablation(
        self,
        asset_returns: pd.DataFrame,
        benchmark_returns: pd.Series,
        variant_weights: dict[AblationVariant, pd.DataFrame],
        *,
        portfolio_id: str | None = None,
    ) -> dict[AblationVariant, tuple[UUID, BacktestResult]]:
        results = self.ablation.run(asset_returns, benchmark_returns, variant_weights)
        persisted = {}
        try:
            for variant, result in results.items():
                backtest_id = self.repository.create(
                    result,
                    portfolio_id=portfolio_id,
                    variant=variant.value,
                    configuration=self.engine.config.model_dump(mode="json"),
                )
                persisted[variant] = (backtest_id, result)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return persisted
