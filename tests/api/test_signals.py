"""Phase 4 API contract tests."""

from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient

from backend.api import signals as signals_api
from backend.dependencies.factor_data import get_factor_data_provider
from backend.main import app
from backend.services.signal_evaluation_service import SignalEvaluationDTO
from quant_engine.risk.models import RiskState
from quant_engine.signals.models import ControlledSignal, ExplainabilityPayload
from quant_engine.volatility.models import MarketRegime

EVALUATION_ID = UUID("22222222-2222-2222-2222-222222222222")
AS_OF_DATE = date(2026, 9, 16)


def result() -> SignalEvaluationDTO:
    risk = RiskState(
        as_of_date=AS_OF_DATE,
        volatility_risk=0.2,
        drawdown_risk=0.3,
        correlation_risk=0.4,
        concentration_risk=0.5,
        liquidity_risk=0.1,
        composite_risk=0.3,
    )
    signal = ControlledSignal(
        ticker="AAPL",
        as_of_date=AS_OF_DATE,
        base_signal=0.5,
        volatility_adjustment=0.9,
        reliability_adjustment=0.8,
        risk_adjustment=0.7,
        controlled_signal=0.252,
    )
    explanation = ExplainabilityPayload(
        ticker="AAPL",
        as_of_date=AS_OF_DATE,
        raw_factors={"ff_alpha": 0.01},
        normalized_factors={"ff_alpha": 1.0},
        factor_contributions={"ff_alpha": 0.5},
        base_signal=0.5,
        effective_reliability=0.72,
        conditional_volatility=0.02,
        volatility_ratio=1.1,
        market_stress=1.0,
        regime=MarketRegime.NORMAL,
        risk_contribution=1.0,
        volatility_adjustment=0.9,
        reliability_adjustment=0.8,
        risk_adjustment=0.7,
        controlled_signal=0.252,
    )
    return SignalEvaluationDTO(
        evaluation_id=EVALUATION_ID,
        portfolio_id="port-phase4",
        as_of_date=AS_OF_DATE,
        risk_state=risk,
        controlled_signals=[signal],
        explainability=[explanation],
    )


class StubService:
    def evaluate(self, portfolio_id, as_of_date, *, evaluation_id=None):
        return result()

    def get_evaluation(self, evaluation_id):
        return result()

    def get_risk(self, evaluation_id):
        return result().risk_state

    def get_explainability(self, evaluation_id):
        return result().explainability


def test_signal_endpoints(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(signals_api, "_service", lambda *args: StubService())
    app.dependency_overrides[get_factor_data_provider] = lambda: object()

    evaluated = client.post(
        "/api/v1/portfolios/port-phase4/signals/evaluate",
        json={"as_of_date": AS_OF_DATE.isoformat(), "evaluation_id": str(EVALUATION_ID)},
    )
    signals = client.get(f"/api/v1/evaluations/{EVALUATION_ID}/signals")
    risk = client.get(f"/api/v1/evaluations/{EVALUATION_ID}/risk")
    explanation = client.get(f"/api/v1/evaluations/{EVALUATION_ID}/explainability")

    assert evaluated.status_code == 201
    assert signals.status_code == 200
    assert signals.json()["controlled_signals"][0]["controlled_signal"] == 0.252
    assert risk.status_code == 200
    assert risk.json()["composite_risk"] == 0.3
    assert explanation.status_code == 200
    assert explanation.json()["items"][0]["raw_factors"] == {"ff_alpha": 0.01}
