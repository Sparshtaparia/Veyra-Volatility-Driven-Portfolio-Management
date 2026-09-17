import logging
from collections.abc import Sequence

import numpy as np

from quant_engine.optimization.models import (
    AssetOptimizationInput,
    OptimizationConstraints,
    OptimizationOutput,
)

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """
    Phase 6 Portfolio Optimizer using CVXPY.

    Objective:
        Maximize: sum(w_i * expected_signal_i)
        Penalty 1: Portfolio variance proxy (w^T * diag(volatility) * w) or sum(w_i^2 * volatility_i)
        Penalty 2: Turnover (sum(|w_i - w_current_i|))

    Note: We use a simplified diagonal variance proxy since we lack full covariance 
    in Phase 5. The risk engine generates composite_risk_score which can also scale the penalty.
    """

    def __init__(
        self,
        risk_aversion: float = 1.0,
        turnover_penalty: float = 0.5,
    ):
        self.risk_aversion = risk_aversion
        self.turnover_penalty = turnover_penalty

    def optimize(
        self,
        inputs: Sequence[AssetOptimizationInput],
        constraints: OptimizationConstraints,
    ) -> list[OptimizationOutput]:
        
        n = len(inputs)
        if n == 0:
            return []

        try:
            import cvxpy as cp
        except ImportError:
            logger.warning("cvxpy not installed, using fallback.")
            return self._fallback_equal_weight(inputs)
        except Exception as e:
            logger.warning(f"cvxpy import failed: {e}, using fallback.")
            return self._fallback_equal_weight(inputs)

        # Extract vectors
        tickers = [x.ticker for x in inputs]
        current_weights = np.array([x.current_weight for x in inputs])
        expected_signals = np.array([x.expected_signal for x in inputs])
        
        # We blend the asset volatility and composite risk score to penalize riskier allocations
        # risk_factor = (volatility_i) * (composite_risk_score_i) * (2.0 - reliability_score_i)
        risk_factors = np.array([
            max(0.01, x.volatility * x.composite_risk_score * (2.0 - x.reliability_score))
            for x in inputs
        ])

        # CVXPY Variables
        w = cp.Variable(n)
        
        # Objective components
        # 1. Maximize expected signal score
        expected_return = expected_signals @ w
        
        # 2. Risk penalty (Diagonal approximation w^T * D * w)
        # cp.sum_squares is scalar if we multiply by sqrt(diag). Wait, w_i^2 * r_i
        risk_penalty = self.risk_aversion * cp.sum(cp.multiply(risk_factors, cp.square(w)))
        
        # 3. Turnover penalty (L1 norm of change)
        turnover = self.turnover_penalty * cp.sum(cp.abs(w - current_weights))
        
        # Objective function
        objective = cp.Maximize(expected_return - risk_penalty - turnover)
        
        # Constraints
        cvx_constraints = [
            cp.sum(w) == 1.0,  # Fully invested
            w >= constraints.min_weight,
            w <= constraints.max_weight,
        ]
        
        # Optional: Turnover Limit
        if constraints.turnover_limit < 1.0:
            # sum of absolute changes / 2 is the actual turnover (if cash is 0).
            # To be safe and simple, we bound sum(|w - w0|) <= 2 * turnover_limit
            cvx_constraints.append(cp.sum(cp.abs(w - current_weights)) <= 2 * constraints.turnover_limit)
        
        # Problem setup and solve
        prob = cp.Problem(objective, cvx_constraints)
        
        try:
            prob.solve(solver=cp.CLARABEL)
        except Exception as e:
            logger.error(f"CVXPY solver exception: {e}")
            return self._fallback_equal_weight(inputs)
            
        if prob.status not in ["optimal", "optimal_inaccurate"]:
            logger.warning(f"Optimization failed with status: {prob.status}. Using fallback.")
            return self._fallback_equal_weight(inputs)
            
        # Extract weights
        optimal_weights = w.value
        
        # Clean up near-zero noise
        optimal_weights = np.clip(optimal_weights, constraints.min_weight, constraints.max_weight)
        optimal_weights = optimal_weights / np.sum(optimal_weights)
        
        outputs = []
        for i, ticker in enumerate(tickers):
            outputs.append(
                OptimizationOutput(
                    ticker=ticker,
                    target_weight=float(optimal_weights[i])
                )
            )
            
        return outputs

    def _fallback_equal_weight(self, inputs: Sequence[AssetOptimizationInput]) -> list[OptimizationOutput]:
        """Simple equal weighting fallback if the optimizer fails."""
        n = len(inputs)
        weight = 1.0 / n if n > 0 else 0.0
        return [OptimizationOutput(ticker=x.ticker, target_weight=weight) for x in inputs]
