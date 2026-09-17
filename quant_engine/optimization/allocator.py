from collections.abc import Sequence

from quant_engine.optimization.models import (
    AllocationDelta,
    AllocationResult,
    AssetOptimizationInput,
    OptimizationOutput,
)


class TargetAllocator:
    """
    Phase 6 Target Allocator.
    
    Responsible for merging current weights with target weights to compute deltas,
    calculating total turnover, and determining the rebalance decision.
    """

    def __init__(self, rebalance_threshold: float = 0.05):
        """
        :param rebalance_threshold: Minimum total turnover (e.g. 0.05 = 5%) 
                                    required to trigger a REBALANCE_REQUIRED decision.
        """
        self.rebalance_threshold = rebalance_threshold

    def allocate(
        self,
        current: Sequence[AssetOptimizationInput],
        targets: Sequence[OptimizationOutput],
    ) -> AllocationResult:
        
        current_map = {x.ticker: x.current_weight for x in current}
        
        allocations = []
        total_abs_change = 0.0
        
        for target in targets:
            c_weight = current_map.get(target.ticker, 0.0)
            delta = target.target_weight - c_weight
            
            allocations.append(
                AllocationDelta(
                    ticker=target.ticker,
                    current_weight=c_weight,
                    target_weight=target.target_weight,
                    delta_weight=delta
                )
            )
            
            total_abs_change += abs(delta)
            
        # Turnover is usually sum(|delta|) / 2 (assuming cash is just a buffer, fully invested)
        # We will use sum(|delta|) / 2 as the standard definition of turnover for long-only.
        turnover = total_abs_change / 2.0
        
        decision = "REBALANCE_REQUIRED" if turnover >= self.rebalance_threshold else "HOLD"
        
        # Ensure floating point stability
        if round(turnover, 6) == 0.0:
            turnover = 0.0
            
        return AllocationResult(
            allocations=allocations,
            total_turnover=turnover,
            decision=decision
        )
