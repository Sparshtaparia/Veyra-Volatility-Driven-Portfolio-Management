<<<<<<< HEAD
from quant_engine.signals.models import BaseSignal, SignalDirection
from quant_engine.signals.service import SignalInputError, SignalService

__all__ = ["BaseSignal", "SignalDirection", "SignalInputError", "SignalService"]
=======
"""State-coupled controlled signal generation."""

from quant_engine.signals.models import ControlledSignal, ExplainabilityPayload, OperatorConfig
from quant_engine.signals.operator import StateCoupledOperator

__all__ = ["ControlledSignal", "ExplainabilityPayload", "OperatorConfig", "StateCoupledOperator"]
>>>>>>> origin/main
