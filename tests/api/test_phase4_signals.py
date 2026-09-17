from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient

from backend.api import volatility as api
from backend.services.signal_evaluation_service import SignalDecisionEvaluationDTO
from quant_engine.control.service import StateCoupledControl
from quant_engine.features.models import FeatureSnapshot
from quant_engine.reliability.models import ReliabilityState
from quant_engine.risk.models import RiskState
from quant_engine.signal_control.service import SignalRegulator
from quant_engine.signals.service import SignalService
from quant_engine.volatility.models import MarketRegime


def test_signal_evaluation_api(client: TestClient, monkeypatch):
    monkeypatch.setattr(api, "require_portfolio_owner", lambda *_args: None)
    base = SignalService().generate(FeatureSnapshot(ticker="TCS", timestamp=date(2026, 9, 16), rsi=70, atr=2, macd_histogram=1, bollinger_band_width=.2))
    control = StateCoupledControl().apply(
        SignalRegulator().regulate(base, regime=MarketRegime.NORMAL, volatility_ratio=1), 
        volatility_state=.02, 
        risk_state=RiskState.LOW_RISK, 
        reliability_state=ReliabilityState.HIGH
    )
    result = SignalDecisionEvaluationDTO(
        UUID("11111111-1111-1111-1111-111111111111"), 
        "port-1", 
        date(2026, 9, 16), 
        [control], 
        {"composite_score": 0.5, "risk_state": "MODERATE_RISK", "components": {"volatility_exposure": 0.5, "concentration": 0.5}}
    )
    class Stub: 
        def evaluate(self, *args, **kwargs): return result
    monkeypatch.setattr(api, "_signal_service", lambda db, provider: Stub())
    response = client.post("/api/v1/portfolios/port-1/signals/evaluate", json={"as_of_date": "2026-09-16"})
    assert response.status_code == 201
    assert response.json()["controls"][0]["ticker"] == "TCS"
    assert response.json()["controls"][0]["decision_state"] == "ADAPT"
