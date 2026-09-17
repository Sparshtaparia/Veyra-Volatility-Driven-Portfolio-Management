"""API contract tests for persisted Phase 3D volatility evaluations."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import volatility as volatility_api
from backend.exceptions import PortfolioNotFoundError, VolatilityEvaluationNotFoundError
from backend.services.volatility_evaluation_service import (
    AssetVolatilityDTO,
    MarketRegimeDTO,
    VolatilityEvaluationDTO,
)
from quant_engine.regimes.exceptions import (
    InsufficientCoverageError,
    InsufficientStressHistoryError,
)
from quant_engine.volatility.models import GARCHFitStatus, MarketRegime

AS_OF_DATE = date(2026, 9, 16)
EVALUATION_ID = UUID("11111111-1111-1111-1111-111111111111")


def evaluation_result() -> VolatilityEvaluationDTO:
    regime = MarketRegimeDTO(
        as_of_date=AS_OF_DATE,
        stress_score=1.1,
        adaptive_threshold=1.2,
        regime=MarketRegime.NORMAL,
        eligible_asset_count=3,
        coverage_ratio=0.75,
        distance_to_threshold=-0.1,
    )
    return VolatilityEvaluationDTO(
        evaluation_id=EVALUATION_ID,
        portfolio_id="port-phase3d",
        as_of_date=AS_OF_DATE,
        market_regime=regime,
        asset_volatility=[
            AssetVolatilityDTO(
                ticker="AAPL",
                conditional_volatility=0.02,
                forecast_volatility=0.021,
                realized_volatility=0.018,
                volatility_ratio=1.1,
                fit_status=GARCHFitStatus.SUCCESS,
                used_fallback=False,
            )
        ],
    )


class StubService:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.result = evaluation_result()

    def _raise_if_needed(self):
        if self.error is not None:
            raise self.error

    def evaluate(self, portfolio_id, as_of_date, *, evaluation_id=None):
        self._raise_if_needed()
        return self.result

    def get_evaluation(self, evaluation_id):
        self._raise_if_needed()
        return self.result

    def get_regime(self, evaluation_id):
        self._raise_if_needed()
        return self.result.market_regime

    def get_latest_regime(self, portfolio_id):
        self._raise_if_needed()
        return self.result.market_regime


def install_stub(monkeypatch: pytest.MonkeyPatch, service: StubService) -> None:
    monkeypatch.setattr(volatility_api, "_service", lambda db, provider: service)
    monkeypatch.setattr(volatility_api, "require_portfolio_owner", lambda *_args: None)
    monkeypatch.setattr(volatility_api, "require_evaluation_owner", lambda *_args: None)


def test_evaluate_endpoint_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    install_stub(monkeypatch, StubService())

    response = client.post(
        "/api/v1/portfolios/port-phase3d/volatility/evaluate",
        json={"as_of_date": AS_OF_DATE.isoformat(), "evaluation_id": str(EVALUATION_ID)},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["evaluation_id"] == str(EVALUATION_ID)
    assert payload["market_regime"]["regime"] == "NORMAL"
    assert payload["asset_volatility"][0]["ticker"] == "AAPL"


def test_unknown_portfolio_maps_to_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_stub(monkeypatch, StubService(PortfolioNotFoundError("missing")))

    response = client.post(
        "/api/v1/portfolios/missing/volatility/evaluate",
        json={"as_of_date": AS_OF_DATE.isoformat()},
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "error",
    [
        InsufficientStressHistoryError(3, 21),
        InsufficientCoverageError(2, 4, 3, 0.5),
    ],
)
def test_quant_input_errors_map_to_422(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    install_stub(monkeypatch, StubService(error))

    response = client.post(
        "/api/v1/portfolios/port-phase3d/volatility/evaluate",
        json={"as_of_date": AS_OF_DATE.isoformat()},
    )

    assert response.status_code == 422


def test_retrieve_evaluation_volatility(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_stub(monkeypatch, StubService())

    response = client.get(f"/api/v1/evaluations/{EVALUATION_ID}/volatility")

    assert response.status_code == 200
    assert response.json()["asset_volatility"][0]["fit_status"] == "SUCCESS"


def test_retrieve_evaluation_regime(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_stub(monkeypatch, StubService())

    response = client.get(f"/api/v1/evaluations/{EVALUATION_ID}/regime")

    assert response.status_code == 200
    assert response.json()["stress_score"] == pytest.approx(1.1)


def test_retrieve_latest_portfolio_regime(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_stub(monkeypatch, StubService())

    response = client.get("/api/v1/portfolios/port-phase3d/regime/latest")

    assert response.status_code == 200
    assert response.json()["as_of_date"] == AS_OF_DATE.isoformat()


def test_missing_volatility_evaluation_maps_to_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_id = uuid4()
    install_stub(monkeypatch, StubService(VolatilityEvaluationNotFoundError(str(missing_id))))

    response = client.get(f"/api/v1/evaluations/{missing_id}/volatility")

    assert response.status_code == 404
