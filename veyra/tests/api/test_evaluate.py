"""
tests/api/test_evaluate.py
==========================
Integration tests for the evaluation API.
"""

from fastapi.testclient import TestClient


def test_full_evaluation_flow(client: TestClient):
    # TEST 1: Create portfolio
    response = client.post("/api/v1/portfolios", json={"name": "Test Portfolio", "currency": "INR"})
    assert response.status_code == 201
    portfolio_data = response.json()
    portfolio_id = portfolio_data["portfolio_id"]
    assert portfolio_id is not None

    # TEST 2: Add TCS holding
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        json={"ticker": "TCS", "quantity": 20, "average_price": 3500, "current_price": 3600},
    )
    assert response.status_code == 201
    tcs_holding = response.json()
    assert tcs_holding["market_value"] == 72000.0

    # TEST 3: Add INFY holding
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        json={"ticker": "INFY", "quantity": 50, "average_price": 1400, "current_price": 1500},
    )
    assert response.status_code == 201
    infy_holding = response.json()
    assert infy_holding["market_value"] == 75000.0

    # TEST 6: POST evaluate
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/evaluate",
        json={"evaluation_date": "2026-09-16", "trigger": "MANUAL"},
    )
    assert response.status_code == 202
    eval_data = response.json()
    evaluation_id = eval_data["evaluation_id"]
    assert evaluation_id is not None
    assert eval_data["status"] == "PENDING"
    assert eval_data["decision"] == "HOLD"
    assert eval_data["portfolio_id"] == portfolio_id

    # TEST 7: GET evaluation
    response = client.get(f"/api/v1/portfolios/{portfolio_id}/evaluations/{evaluation_id}")
    assert response.status_code == 200
    get_eval_data = response.json()
    assert get_eval_data["evaluation_id"] == evaluation_id

    # TEST 8: Request nonexistent portfolio
    response = client.post(
        "/api/v1/portfolios/fake_portfolio/evaluate",
        json={"evaluation_date": "2026-09-16", "trigger": "MANUAL"},
    )
    assert response.status_code == 404

    # TEST 9: Request nonexistent evaluation
    response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/evaluations/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404

    # TEST 10: Verify evaluation belongs to requested portfolio
    # Create another portfolio
    response = client.post("/api/v1/portfolios", json={"name": "P2", "currency": "INR"})
    p2_id = response.json()["portfolio_id"]

    response = client.get(f"/api/v1/portfolios/{p2_id}/evaluations/{evaluation_id}")
    assert response.status_code == 404
