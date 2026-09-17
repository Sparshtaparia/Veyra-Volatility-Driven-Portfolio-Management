import pytest

from quant_engine.reliability.models import ReliabilityState
from quant_engine.reliability.service import ReliabilityService


def test_reliability_bounds_and_decay():
    service = ReliabilityService(kappa=1.0)

    # Zero volatility -> full reliability
    result_zero = service.compute_reliability("AAPL", 0.0)
    assert result_zero.reliability_score == 1.0
    assert result_zero.reliability_state == ReliabilityState.HIGH

    # High volatility -> lower reliability
    result_high = service.compute_reliability("AAPL", 1.0)
    assert result_high.reliability_score < 1.0
    assert result_high.reliability_score > 0.0

    # Very high volatility -> low reliability
    result_very_high = service.compute_reliability("AAPL", 5.0)
    assert result_very_high.reliability_score < 0.1
    assert result_very_high.reliability_state == ReliabilityState.LOW


def test_invalid_volatility():
    service = ReliabilityService()
    with pytest.raises(ValueError, match="cannot be negative"):
        service.compute_reliability("AAPL", -1.0)


def test_invalid_kappa():
    with pytest.raises(ValueError, match="strictly positive"):
        ReliabilityService(kappa=0.0)
