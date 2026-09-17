"""Golden user journey over the real quant, persistence, and HTTP layers."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dependencies.auth import CurrentUser, require_auth
from backend.dependencies.market_data import get_market_data_provider
from backend.main import app
from database.models import (
    EvaluationModel,
    FeedbackUpdateModel,
    PortfolioSnapshotModel,
    RebalanceEventModel,
    RegimeStateModel,
    TradeModel,
    VolatilityStateModel,
)
from tests.integration.golden_scenario import (
    FIRST_EVALUATION_DATE,
    SECOND_EVALUATION_DATE,
    GoldenMarketProvider,
    demo_holdings,
)


def test_user_evaluation_rebalance_feedback_next_evaluation(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = GoldenMarketProvider()
    app.dependency_overrides[get_market_data_provider] = lambda: provider

    created = client.post(
        "/api/v1/portfolios",
        json={"name": "Golden Demo", "currency": "USD"},
    )
    assert created.status_code == 201
    portfolio_id = created.json()["portfolio_id"]

    for holding in demo_holdings(provider):
        response = client.post(
            f"/api/v1/portfolios/{portfolio_id}/holdings",
            json=holding,
        )
        assert response.status_code == 201

    # A different authenticated user must not learn whether this portfolio exists.
    owner_dependency = app.dependency_overrides[require_auth]
    app.dependency_overrides[require_auth] = lambda: CurrentUser(
        user_id="other-user",
        email="other@example.com",
        role="INVESTOR",
    )
    forbidden = client.get(f"/api/v1/portfolios/{portfolio_id}")
    assert forbidden.status_code == 404
    app.dependency_overrides[require_auth] = owner_dependency

    first = client.post(
        f"/api/v1/portfolios/{portfolio_id}/signals/evaluate",
        json={"as_of_date": FIRST_EVALUATION_DATE.isoformat()},
    )
    assert first.status_code == 201, first.text
    first_payload = first.json()
    assert first_payload["allocation_result"]["decision"] == "REBALANCE_REQUIRED"
    first_evaluation_id = UUID(first_payload["evaluation_id"])

    unapproved = client.post(
        f"/api/v1/portfolios/{portfolio_id}/rebalance",
        json={
            "as_of_date": FIRST_EVALUATION_DATE.isoformat(),
            "evaluation_id": str(first_evaluation_id),
            "approved": False,
        },
    )
    assert unapproved.status_code == 422

    history = client.get(f"/api/v1/portfolios/{portfolio_id}/evaluations")
    assert history.status_code == 200
    assert history.json()[0]["decision"] == "REBALANCE"

    execution = client.post(
        f"/api/v1/portfolios/{portfolio_id}/rebalance",
        json={
            "as_of_date": FIRST_EVALUATION_DATE.isoformat(),
            "evaluation_id": str(first_evaluation_id),
            "approved": True,
        },
    )
    assert execution.status_code == 201, execution.text
    execution_payload = execution.json()
    assert execution_payload["evaluation_id"] == str(first_evaluation_id)
    assert execution_payload["orders"]
    assert all(order["status"] == "FILLED" for order in execution_payload["orders"])

    feedback = client.get(f"/api/v1/portfolios/{portfolio_id}/feedback")
    assert feedback.status_code == 200
    feedback_payload = feedback.json()
    assert feedback_payload["updated_threshold"] != pytest.approx(
        feedback_payload["previous_threshold"]
    )

    second = client.post(
        f"/api/v1/portfolios/{portfolio_id}/signals/evaluate",
        json={"as_of_date": SECOND_EVALUATION_DATE.isoformat()},
    )
    assert second.status_code == 201, second.text
    second_evaluation_id = UUID(second.json()["evaluation_id"])

    second_regime = db_session.scalar(
        select(RegimeStateModel).where(
            RegimeStateModel.evaluation_id == second_evaluation_id
        )
    )
    assert second_regime is not None
    assert second_regime.adaptive_threshold == pytest.approx(
        feedback_payload["updated_threshold"]
    )

    assert len(
        db_session.scalars(
            select(EvaluationModel).where(EvaluationModel.portfolio_id == portfolio_id)
        ).all()
    ) == 2
    assert len(
        db_session.scalars(
            select(VolatilityStateModel).where(
                VolatilityStateModel.portfolio_id == portfolio_id
            )
        ).all()
    ) == 6
    event = db_session.scalar(
        select(RebalanceEventModel).where(
            RebalanceEventModel.evaluation_id == first_evaluation_id
        )
    )
    assert event is not None
    assert db_session.scalars(select(TradeModel).where(TradeModel.event_id == event.event_id)).all()
    assert db_session.scalar(
        select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.evaluation_id == first_evaluation_id
        )
    ) is not None
    assert db_session.scalar(
        select(FeedbackUpdateModel).where(
            FeedbackUpdateModel.evaluation_id == first_evaluation_id
        )
    ) is not None
