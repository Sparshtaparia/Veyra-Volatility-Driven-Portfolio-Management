"""Convex long-only optimizer anchored to inverse-volatility sizing."""

from datetime import date
from math import sqrt

import cvxpy as cp
import numpy as np

from quant_engine.portfolio.models import (
    AssetAllocationInput,
    ExposureState,
    OptimizationResult,
    OptimizerConfig,
    TargetWeight,
)


class PortfolioOptimizer:
    def __init__(self, config: OptimizerConfig | None = None) -> None:
        self.config = config or OptimizerConfig()

    def optimize(
        self,
        as_of_date: date,
        assets: list[AssetAllocationInput],
        exposure: ExposureState,
    ) -> OptimizationResult:
        if not assets:
            raise ValueError("optimizer requires at least one asset")
        volatilities = np.asarray([asset.conditional_volatility for asset in assets])
        inverse_volatility = 1.0 / volatilities
        maximum_gross = min(
            exposure.target_gross_exposure,
            1.0 - self.config.minimum_cash_weight,
            len(assets) * self.config.max_stock_weight,
            len({asset.sector for asset in assets}) * self.config.max_sector_exposure,
        )
        baseline = inverse_volatility / inverse_volatility.sum() * maximum_gross
        current = np.asarray([asset.current_weight for asset in assets])
        signals = np.asarray([asset.controlled_signal for asset in assets])
        annual_covariance = np.diag((volatilities * sqrt(252.0)) ** 2)

        weights = cp.Variable(len(assets))
        objective = cp.Minimize(
            self.config.baseline_penalty * cp.sum_squares(weights - baseline)
            + self.config.turnover_penalty * cp.norm1(weights - current)
            - self.config.signal_strength * signals @ weights
        )
        constraints = [
            weights >= 0.0,
            weights <= self.config.max_stock_weight,
            cp.sum(weights) <= maximum_gross,
            cp.quad_form(weights, annual_covariance) <= self.config.target_volatility**2,
        ]
        for sector in sorted({asset.sector for asset in assets}):
            indices = [index for index, asset in enumerate(assets) if asset.sector == sector]
            constraints.append(cp.sum(weights[indices]) <= self.config.max_sector_exposure)
        problem = cp.Problem(objective, constraints)
        problem.solve(solver=cp.CLARABEL)
        if weights.value is None or problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            raise ValueError(f"portfolio optimization failed: {problem.status}")
        solved = np.maximum(np.asarray(weights.value).reshape(-1), 0.0)
        gross = float(solved.sum())
        expected_volatility = float(sqrt(solved @ annual_covariance @ solved))
        targets = [
            TargetWeight(
                ticker=asset.ticker,
                sector=asset.sector,
                current_weight=asset.current_weight,
                inverse_volatility_weight=float(baseline[index]),
                target_weight=float(solved[index]),
                weight_change=float(solved[index] - current[index]),
            )
            for index, asset in enumerate(assets)
        ]
        return OptimizationResult(
            as_of_date=as_of_date,
            targets=targets,
            gross_exposure=gross,
            net_exposure=gross,
            cash_weight=1.0 - gross,
            expected_volatility=expected_volatility,
            expected_turnover=float(np.abs(solved - current).sum()),
            solver_status=str(problem.status),
        )
