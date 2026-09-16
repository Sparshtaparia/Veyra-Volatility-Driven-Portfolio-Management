import math

from quant_engine.risk.models import CompositeRiskOutput, RiskComponents, RiskState


class CompositeRiskService:
    """
    Computes portfolio-level composite risk state.
    """

    def __init__(self, weight_vol: float = 0.6, weight_conc: float = 0.4):
        if not math.isclose(weight_vol + weight_conc, 1.0, rel_tol=1e-5):
            raise ValueError("Weights must sum to 1.0")
        self.weight_vol = weight_vol
        self.weight_conc = weight_conc

    def compute_risk(self, portfolio_id: str, holdings: list[dict], asset_volatilities: dict[str, float]) -> CompositeRiskOutput:
        """
        Computes the composite risk score using volatility exposure and concentration.
        
        Args:
            portfolio_id: The portfolio ID.
            holdings: A list of dicts with 'ticker' and 'weight'.
            asset_volatilities: A dictionary mapping ticker to its volatility state.
        """
        if not holdings:
            return CompositeRiskOutput(
                portfolio_id=portfolio_id,
                composite_score=0.0,
                risk_state=RiskState.LOW_RISK,
                components=RiskComponents(volatility_exposure=0.0, concentration=0.0)
            )

        # 1. Concentration Risk (Herfindahl-Hirschman Index normalized)
        # HHI = sum(w^2). Max is 1.0 (single asset), min is 1/N.
        hhi = sum(h["weight"]**2 for h in holdings)
        # Normalize concentration: (HHI - 1/N) / (1 - 1/N) if N > 1 else 1.0
        n = len(holdings)
        if n > 1:
            concentration = (hhi - 1.0/n) / (1.0 - 1.0/n)
        else:
            concentration = 1.0

        # 2. Volatility Exposure
        # Weighted average of asset volatilities, then passed through a sigmoid or bounded function.
        # We assume volatility_state typically ranges from 0 to something like 2.0-3.0.
        # We'll normalize it using a bounded function: 1 - exp(-k * avg_vol)
        avg_vol = sum(h["weight"] * asset_volatilities.get(h["ticker"], 0.0) for h in holdings)
        # Assuming avg_vol ~ 1.0 is normal, we scale it.
        vol_exposure = 1.0 - math.exp(-0.5 * avg_vol)

        # 3. Nonlinear Interaction (Volatility-Concentration)
        # As per docs, high volatility and high concentration interact multiplicatively.
        interaction = vol_exposure * concentration

        # 4. Composite Score
        base_score = self.weight_vol * vol_exposure + self.weight_conc * concentration
        # Add nonlinear penalty, bounded to 1.0
        score = min(1.0, base_score + 0.5 * interaction)

        # 5. Risk State Mapping
        if score >= 0.75:
            state = RiskState.CRITICAL_RISK
        elif score >= 0.50:
            state = RiskState.ELEVATED_RISK
        elif score >= 0.25:
            state = RiskState.MODERATE_RISK
        else:
            state = RiskState.LOW_RISK

        return CompositeRiskOutput(
            portfolio_id=portfolio_id,
            composite_score=score,
            risk_state=state,
            components=RiskComponents(
                volatility_exposure=vol_exposure,
                concentration=concentration
            )
        )
