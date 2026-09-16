import math

from quant_engine.reliability.models import ReliabilityLevel, ReliabilityOutput


class ReliabilityService:
    """
    Computes the signal reliability for an asset based on its volatility state.
    Formula: W_i,t = exp(-kappa * sigma_i,t)
    """

    def __init__(self, kappa: float = 1.0):
        if kappa <= 0:
            raise ValueError("kappa must be strictly positive")
        self.kappa = kappa

    def compute_reliability(self, ticker: str, sigma_it: float) -> ReliabilityOutput:
        """
        Computes the bounded reliability score and assigns a state.
        
        Args:
            ticker: Asset ticker symbol.
            sigma_it: The asset's volatility state.
        """
        if sigma_it < 0:
            raise ValueError("sigma_it (volatility) cannot be negative")

        score = math.exp(-self.kappa * sigma_it)

        # Discretize into states for the control operator
        if score >= 0.75:
            state = ReliabilityLevel.HIGH
        elif score >= 0.40:
            state = ReliabilityLevel.MODERATE
        else:
            state = ReliabilityLevel.LOW

        return ReliabilityOutput(
            ticker=ticker,
            sigma_it=sigma_it,
            kappa=self.kappa,
            reliability_score=score,
            reliability_state=state
        )
