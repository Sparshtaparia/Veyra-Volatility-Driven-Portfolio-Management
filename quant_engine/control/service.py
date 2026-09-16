"""Deterministic state-coupled control operator U = Phi(S, volatility, risk, reliability)."""
from quant_engine.control.models import ControlOutput, DecisionState
from quant_engine.reliability.models import ReliabilityLevel
from quant_engine.risk.models import RiskLevel
from quant_engine.signal_control.models import RegulatedSignal
from quant_engine.signals.models import SignalDirection
from quant_engine.volatility.models import MarketRegime


class StateCoupledControl:
    regime_multipliers = {MarketRegime.LOW_VOL: 1.0, MarketRegime.NORMAL: 1.0, MarketRegime.ELEVATED: 0.80, MarketRegime.HIGH_STRESS: 0.55}
    risk_multipliers = {RiskLevel.LOW_RISK: 1.0, RiskLevel.MODERATE_RISK: 0.8, RiskLevel.ELEVATED_RISK: 0.5, RiskLevel.CRITICAL_RISK: 0.1}
    reliability_multipliers = {ReliabilityLevel.HIGH: 1.0, ReliabilityLevel.MODERATE: 0.7, ReliabilityLevel.LOW: 0.3}

    def apply(self, regulated: RegulatedSignal, *, volatility_state: float, risk_state: RiskLevel, reliability_state: ReliabilityLevel) -> ControlOutput:
        if volatility_state < 0:
            raise ValueError("volatility_state must be non-negative")
        multiplier = self.regime_multipliers[regulated.regime] * self.risk_multipliers[risk_state] * self.reliability_multipliers[reliability_state]
        output = regulated.regulated_signal * multiplier
        magnitude = abs(output)
        if magnitude < 0.10:
            decision, direction, reasons = DecisionState.HOLD, SignalDirection.NEUTRAL, ["SIGNAL_BELOW_ACTION_THRESHOLD"]
        elif regulated.regime is MarketRegime.HIGH_STRESS:
            decision, direction, reasons = DecisionState.REVIEW, regulated.direction, ["HIGH_VOLATILITY_REVIEW", "SIGNAL_ATTENUATED"]
        elif magnitude >= 0.35:
            decision, direction, reasons = DecisionState.ADAPT, regulated.direction, ["ACTIONABLE_SIGNAL", "NORMAL_CONTROL_CONDITIONS"]
        else:
            decision, direction, reasons = DecisionState.REVIEW, regulated.direction, ["MODERATE_SIGNAL_REQUIRES_REVIEW"]
        return ControlOutput(regulated_signal=regulated, volatility_state=volatility_state, regime=regulated.regime, risk_state=risk_state, reliability_state=reliability_state, control_output=output, direction=direction, decision_state=decision, reason_codes=reasons)
