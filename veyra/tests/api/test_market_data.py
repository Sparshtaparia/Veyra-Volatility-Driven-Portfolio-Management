"""
tests/api/test_market_data.py
=============================
Integration tests for the market data API.
"""

from fastapi.testclient import TestClient
import pytest

def test_get_portfolio_features_invalid_portfolio(client: TestClient):
    response = client.get("/api/v1/portfolios/fake_port/features?ticker=AAPL&start_date=2023-01-01&end_date=2023-12-31")
    assert response.status_code == 404

def test_get_portfolio_features_invalid_ticker(client: TestClient):
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Test Portfolio", "currency": "INR"}
    )
    portfolio_id = response.json()["portfolio_id"]
    
    # Request features for a ticker not in the portfolio
    response = client.get(f"/api/v1/portfolios/{portfolio_id}/features?ticker=AAPL&start_date=2023-01-01&end_date=2023-12-31")
    assert response.status_code == 404
    assert "not found in portfolio" in response.json()["detail"]

# A full integration test with YFinance is not reliable in CI without mocking the external call.
# The provider is already unit tested with a MockProvider, and the API logic is tested above.
