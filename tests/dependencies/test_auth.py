"""Supabase Bearer-token and ownership boundary tests."""

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.dependencies import auth
from backend.dependencies.auth import CurrentUser, require_auth
from backend.dependencies.db import get_db
from backend.exceptions import PortfolioNotFoundError
from backend.main import app
from backend.services.portfolio_service import PortfolioService
from config.settings import Settings
from database.repositories.portfolio_repo import PortfolioRepository


def _client() -> TestClient:
    app = FastAPI()

    @app.get("/protected")
    def protected(user: CurrentUser = Depends(require_auth)):
        return {"user_id": user.user_id, "email": user.email, "role": user.role}

    return TestClient(app)


def test_missing_bearer_token_is_rejected() -> None:
    response = _client().get("/protected")
    assert response.status_code == 401


def test_development_bypass_returns_stable_user_without_token(monkeypatch) -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        app_env="development",
        auth_bypass_enabled=True,
        dev_auth_user_id="00000000-0000-0000-0000-000000000001",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)

    response = _client().get("/protected")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "dev@veyra.local",
        "role": "INVESTOR",
    }


def test_development_bypass_authenticates_portfolio_creation(monkeypatch, db_session) -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        app_env="development",
        auth_bypass_enabled=True,
        dev_auth_user_id="00000000-0000-0000-0000-000000000001",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/portfolios",
                json={"name": "Development", "currency": "USD"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    portfolio = PortfolioRepository(db_session).get_portfolio(response.json()["portfolio_id"])
    assert portfolio is not None
    assert portfolio.user_id == "00000000-0000-0000-0000-000000000001"


def test_development_bypass_disabled_still_requires_token(monkeypatch) -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        app_env="development",
        auth_bypass_enabled=False,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    assert _client().get("/protected").status_code == 401


def test_production_rejects_auth_bypass() -> None:
    try:
        Settings(
            database_url="postgresql://user:password@example.test/veyra",
            app_env="production",
            api_key="x" * 32,
            auth_bypass_enabled=True,
        )
    except ValidationError as exc:
        assert "AUTH_BYPASS_ENABLED cannot be enabled in production" in str(exc)
    else:
        raise AssertionError("production auth bypass was accepted")


def test_production_without_bypass_still_requires_token(monkeypatch) -> None:
    settings = Settings(
        database_url="postgresql://user:password@example.test/veyra",
        app_env="production",
        api_key="x" * 32,
        auth_bypass_enabled=False,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    assert _client().get("/protected").status_code == 401


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
