import pytest
from quant_engine.risk.models import RiskState
from quant_engine.risk.service import CompositeRiskService


def test_composite_risk_empty_holdings():
    service = CompositeRiskService()
    result = service.compute_risk("port-1", [], {})
    assert result.composite_score == 0.0
    assert result.risk_state == RiskState.LOW_RISK


def test_composite_risk_single_asset():
    service = CompositeRiskService()
    holdings = [{"ticker": "AAPL", "weight": 1.0}]
    vols = {"AAPL": 0.5}
    
    result = service.compute_risk("port-1", holdings, vols)
    
    # Concentration should be 1.0
    assert result.components.concentration == 1.0
    assert result.components.volatility_exposure > 0.0
    assert result.composite_score > 0.0
    assert result.composite_score <= 1.0


def test_composite_risk_diversified():
    service = CompositeRiskService()
    holdings = [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.5},
    ]
    vols = {"AAPL": 0.1, "MSFT": 0.1}
    
    result = service.compute_risk("port-1", holdings, vols)
    
    # HHI is 0.5, N=2, so concentration is 0.0
    assert result.components.concentration == 0.0
    assert result.components.volatility_exposure < 0.1 # Very low vol
    assert result.risk_state == RiskState.LOW_RISK


def test_invalid_weights():
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        CompositeRiskService(weight_vol=0.5, weight_conc=0.4)
