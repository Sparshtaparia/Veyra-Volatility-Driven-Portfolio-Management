"""Phase 5 upload, portfolio-control, feedback, and backtest API tests."""

from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient

from backend.api import portfolio_control as api
from backend.dependencies.market_data import get_market_data_provider
from backend.main import app
from backend.services.portfolio_control_service import PortfolioControlDTO
from quant_engine.data.models import MarketBar
from quant_engine.feedback.models import FeedbackOutcome, FeedbackUpdate, SystemState
from quant_engine.portfolio.models import OptimizationResult
from tests.services.test_signal_evaluation_service import IntegrationProvider

EVALUATION_ID = UUID("55555555-5555-5555-5555-555555555555")
EVENT_ID = UUID("66666666-6666-6666-6666-666666666666")


def test_manual_and_csv_upload_endpoints(client: TestClient) -> None:
    provider = IntegrationProvider(
        [
            MarketBar(
                ticker="AAA",
                timestamp=date(2026, 1, 2),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1_000.0,
            )
        ]
    )
    app.dependency_overrides[get_market_data_provider] = lambda: provider

    manual = client.post(
        "/api/v1/portfolios/manual",
        json={
            "name": "Manual",
            "currency": "USD",
            "as_of_date": "2026-01-02",
            "holdings": [{"ticker": "AAA", "quantity": 2, "average_price": 90}],
        },
    )
    uploaded = client.post(
        "/api/v1/portfolios/upload",
        data={"name": "CSV", "currency": "USD", "as_of_date": "2026-01-02"},
        files={
            "file": (
                "holdings.csv",
                b"ticker,quantity,average_price\nAAA,3,95\n",
                "text/csv",
            )
        },
    )

    assert manual.status_code == 201
    assert manual.json()["total_value"] == 200.0
    assert uploaded.status_code == 201
    portfolio_id = uploaded.json()["portfolio_id"]
    retrieved = client.get(f"/api/v1/portfolios/{portfolio_id}/holdings")
    assert retrieved.status_code == 200
    assert retrieved.json()["holdings"][0]["weight"] == 1.0


class StubPortfolioControlService:
    def __init__(self, _db) -> None:
        pass

    def optimize_and_rebalance(self, portfolio_id, evaluation_id, **_kwargs):
        return PortfolioControlDTO(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            optimization=OptimizationResult(
                as_of_date=date(2026, 1, 2),
                targets=[
                    {
                        "ticker": "AAA",
                        "sector": "TECH",
                        "current_weight": 1.0,
                        "inverse_volatility_weight": 0.7,
                        "target_weight": 0.7,
                        "weight_change": -0.3,
                    }
                ],
                gross_exposure=0.7,
                net_exposure=0.7,
                cash_weight=0.3,
                expected_volatility=0.1,
                expected_turnover=0.3,
                solver_status="optimal",
            ),
            trades=[],
            rebalance_event_id=EVENT_ID,
        )

    def apply_feedback(self, _portfolio_id, _evaluation_id, outcome):
        previous = SystemState(
            as_of_date=date(2026, 1, 2),
            volatility_distribution_level=0.02,
            adaptive_threshold=1.0,
            reliability_multiplier=0.8,
            risk_limit=0.6,
            exposure_limit=0.7,
            portfolio_value=10_000.0,
        )
        return FeedbackUpdate(
            previous_state=previous,
            controlled_signal=0.2,
            outcome=outcome,
            updated_state=previous.model_copy(update={"as_of_date": outcome.observation_date}),
        )


def test_control_and_feedback_api_contracts(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(api, "PortfolioControlService", StubPortfolioControlService)
    monkeypatch.setattr(api, "require_portfolio_owner", lambda *_args: None)
    optimized = client.post(
        "/api/v1/portfolios/port-test/optimize",
        json={
            "evaluation_id": str(EVALUATION_ID),
            "sectors": {"AAA": "TECH"},
            "optimizer_config": {"max_stock_weight": 0.8},
            "transaction_cost_bps": 4,
            "slippage_bps": 1,
        },
    )
    feedback = client.post(
        "/api/v1/portfolios/port-test/feedback",
        json={
            "evaluation_id": str(EVALUATION_ID),
            "outcome": FeedbackOutcome(
                observation_date=date(2026, 2, 2),
                portfolio_return=0.01,
                realized_volatility=0.02,
                drawdown=0.01,
                signal_accuracy=0.5,
                transaction_cost=1.0,
            ).model_dump(mode="json"),
        },
    )

    assert optimized.status_code == 201
    assert optimized.json()["optimization"]["cash_weight"] == 0.3
    assert feedback.status_code == 200
    assert feedback.json()["updated_state"]["as_of_date"] == "2026-02-02"


def test_backtest_create_and_get_endpoints(client: TestClient) -> None:
    dates = [f"2025-01-{day:02d}" for day in range(1, 29)] + [
        f"2025-02-{day:02d}" for day in range(1, 11)
    ]
    response = client.post(
        "/api/v1/backtests",
        json={
            "name": "API walk forward",
            "return_dates": dates,
            "asset_returns": {"AAA": [0.001] * len(dates)},
            "signal_dates": [dates[0]],
            "target_weights": {"AAA": [0.5]},
            "benchmark_returns": [0.0002] * len(dates),
        },
    )

    assert response.status_code == 201
    backtest_id = response.json()["backtest_id"]
    retrieved = client.get(f"/api/v1/backtests/{backtest_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["status"] == "COMPLETED"
    assert retrieved.json()["metrics"]["turnover"] > 0.0
