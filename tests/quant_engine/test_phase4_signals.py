from datetime import date
import pytest
from quant_engine.control.models import DecisionState
from quant_engine.control.service import StateCoupledControl
from quant_engine.features.models import FeatureSnapshot
from quant_engine.signal_control.service import SignalRegulator
from quant_engine.signals.models import SignalDirection
from quant_engine.signals.service import SignalInputError, SignalService
from quant_engine.volatility.models import MarketRegime


def feature(**changes):
    values = dict(ticker="TCS", timestamp=date(2026, 9, 16), rsi=70.0, atr=2.0, macd_histogram=1.0, bollinger_band_width=0.2)
    values.update(changes)
    return FeatureSnapshot(**values)


def test_signal_is_interpretable_and_deterministic():
    service = SignalService()
    first, second = service.generate(feature()), service.generate(feature())
    assert first == second
    assert first.direction is SignalDirection.BUY
    assert first.components.rsi == pytest.approx(0.4)
    assert first.components.macd_momentum > 0


def test_signal_rejects_incomplete_or_invalid_features():
    with pytest.raises(SignalInputError): SignalService().generate(feature(rsi=None))
    with pytest.raises(SignalInputError): SignalService().generate(feature(atr=0))


def test_attenuation_is_bounded_and_high_stress_reduces_signal():
    base = SignalService().generate(feature())
    regulator = SignalRegulator()
    normal = regulator.regulate(base, regime=MarketRegime.NORMAL, volatility_ratio=1.2)
    stressed = regulator.regulate(base, regime=MarketRegime.HIGH_STRESS, volatility_ratio=2.5)
    assert normal.attenuation_factor == 1.0
    assert 0 < stressed.attenuation_factor <= 1
    assert abs(stressed.regulated_signal) < abs(normal.regulated_signal)
    assert stressed.direction is base.direction


def test_control_operator_responds_to_available_regime_state():
    base = SignalService().generate(feature(rsi=85, macd_histogram=2))
    regulator = SignalRegulator()
    normal = StateCoupledControl().apply(regulator.regulate(base, regime=MarketRegime.NORMAL, volatility_ratio=1), volatility_state=.02)
    stressed = StateCoupledControl().apply(regulator.regulate(base, regime=MarketRegime.HIGH_STRESS, volatility_ratio=2), volatility_state=.08)
    assert normal.control_output != stressed.control_output
    assert normal.decision_state is DecisionState.ADAPT
    assert stressed.decision_state in (DecisionState.HOLD, DecisionState.REVIEW)
