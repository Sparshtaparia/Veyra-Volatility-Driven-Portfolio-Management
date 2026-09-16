"""Supabase Bearer-token and ownership boundary tests."""

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.dependencies import auth
from backend.dependencies.auth import CurrentUser, require_auth
from backend.exceptions import PortfolioNotFoundError
from backend.services.portfolio_service import PortfolioService


def _client() -> TestClient:
    app = FastAPI()

    @app.get("/protected")
    def protected(user: CurrentUser = Depends(require_auth)):
        return {"user_id": user.user_id, "email": user.email, "role": user.role}

    return TestClient(app)


def test_missing_bearer_token_is_rejected() -> None:
    response = _client().get("/protected")
    assert response.status_code == 401


def test_verified_bearer_token_uses_subject_as_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_decode_token",
        lambda _token: {"sub": "supabase-user", "email": "user@example.com"},
    )
    response = _client().get("/protected", headers={"Authorization": "Bearer valid.jwt"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "supabase-user"


def test_invalid_and_expired_bearer_tokens_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        auth, "_decode_token", lambda _token: (_ for _ in ()).throw(jwt.InvalidTokenError())
    )
    response = _client().get("/protected", headers={"Authorization": "Bearer invalid.jwt"})
    assert response.status_code == 401

    monkeypatch.setattr(
        auth,
        "_decode_token",
        lambda _token: (_ for _ in ()).throw(jwt.ExpiredSignatureError()),
    )
    response = _client().get("/protected", headers={"Authorization": "Bearer expired.jwt"})
    assert response.status_code == 401


def test_portfolio_service_enforces_authenticated_owner(db_session) -> None:
    service = PortfolioService(db_session)
    portfolio = service.create_portfolio("Owned", "USD", user_id="owner-id")
    assert service.get_portfolio(portfolio.id, user_id="owner-id").id == portfolio.id

    try:
        service.get_portfolio(portfolio.id, user_id="different-user")
    except PortfolioNotFoundError:
        pass
    else:
        raise AssertionError("a different Supabase subject accessed the portfolio")
