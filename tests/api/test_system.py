"""Operational and persisted evaluation-history API tests."""

from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.portfolio_repo import PortfolioRepository
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger


def test_liveness_readiness_and_system_status(client: TestClient) -> None:
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    status = client.get("/api/v1/system/status")

    assert live.status_code == 200
    assert live.json() == {"status": "live"}
    assert ready.status_code == 503
    assert ready.json()["schema_status"] == "migration_required"
    assert status.status_code == 200
    assert status.json()["market_data"]["provider"] == "yfinance->yahoo_chart"
    assert "metrics" in status.json()


def test_evaluation_history_is_persisted_and_ordered(
    client: TestClient, db_session: Session
) -> None:
    portfolio_id = f"port-{uuid4().hex[:8]}"
    PortfolioRepository(db_session).create_portfolio(
        portfolio_id, "History", "USD", user_id="test-user"
    )
    repository = EvaluationRepository(db_session)
    for evaluation_date in (date(2026, 1, 1), date(2026, 2, 1)):
        repository.create_evaluation(
            uuid4(),
            portfolio_id,
            evaluation_date,
            EvaluationTrigger.SCHEDULED,
            EvaluationDecision.HOLD,
            EvaluationStatus.COMPLETED,
        )

    response = client.get(f"/api/v1/portfolios/{portfolio_id}/evaluations")

    assert response.status_code == 200
    assert [item["evaluation_date"] for item in response.json()] == [
        "2026-02-01",
        "2026-01-01",
    ]
