"""Supabase Bearer-token and ownership boundary tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
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
        local_development=True,
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
        local_development=True,
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
            auth_bypass_enabled=True,
            local_development=True,
        )
    except ValidationError as exc:
        assert "AUTH_BYPASS_ENABLED requires APP_ENV=development/test" in str(exc)
    else:
        raise AssertionError("production auth bypass was accepted")


def test_production_without_bypass_still_requires_token(monkeypatch) -> None:
    settings = Settings(
        database_url="postgresql://user:password@example.test/veyra",
        app_env="production",
        supabase_url="https://project.supabase.co",
        supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
        cors_origins=["https://app.example.test"],
        trusted_hosts=["api.example.test"],
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


def test_user_metadata_cannot_self_assign_admin_role(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_decode_token",
        lambda _token: {
            "sub": "supabase-user",
            "email": "user@example.com",
            "user_metadata": {"role": "ADMIN"},
        },
    )
    response = _client().get("/protected", headers={"Authorization": "Bearer valid.jwt"})
    assert response.status_code == 200
    assert response.json()["role"] == "INVESTOR"


def test_trusted_app_metadata_assigns_admin_role(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_decode_token",
        lambda _token: {
            "sub": "supabase-admin",
            "email": "admin@example.com",
            "app_metadata": {"role": "ADMIN"},
        },
    )
    response = _client().get("/protected", headers={"Authorization": "Bearer valid.jwt"})
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


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


def test_staging_rejects_auth_bypass() -> None:
    with pytest.raises(ValidationError, match="AUTH_BYPASS_ENABLED requires"):
        Settings(
            database_url="postgresql://user:password@example.test/veyra",
            app_env="staging",
            auth_bypass_enabled=True,
            local_development=True,
        )


def test_bypass_requires_explicit_local_development() -> None:
    with pytest.raises(ValidationError, match="LOCAL_DEVELOPMENT=true"):
        Settings(
            database_url="sqlite:///:memory:",
            app_env="development",
            auth_bypass_enabled=True,
        )


def test_legacy_unowned_portfolio_is_not_visible_to_authenticated_user(db_session) -> None:
    service = PortfolioService(db_session)
    portfolio = service.create_portfolio("Legacy", "USD")
    with pytest.raises(PortfolioNotFoundError):
        service.get_portfolio(portfolio.id, user_id="authenticated-user")


def _signed_token(private_key, *, issuer: str, expires_at: datetime) -> str:
    return jwt.encode(
        {
            "sub": "verified-user",
            "email": "verified@example.com",
            "iss": issuer,
            "aud": "authenticated",
            "exp": expires_at,
        },
        private_key,
        algorithm="RS256",
    )


def test_jwks_verification_accepts_expected_supabase_issuer_and_rejects_wrong_project(
    monkeypatch,
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    settings = Settings(
        database_url="sqlite:///:memory:",
        app_env="test",
        supabase_url="https://expected.supabase.co",
        supabase_jwks_url="https://expected.supabase.co/auth/v1/.well-known/jwks.json",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth,
        "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key)
        ),
    )

    valid = _signed_token(
        private_key,
        issuer="https://expected.supabase.co/auth/v1",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert auth._decode_token(valid)["sub"] == "verified-user"

    wrong_project = _signed_token(
        private_key,
        issuer="https://other.supabase.co/auth/v1",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    with pytest.raises(jwt.InvalidIssuerError):
        auth._decode_token(wrong_project)


def test_verified_jwt_expiration_is_enforced(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        database_url="sqlite:///:memory:",
        app_env="test",
        supabase_url="https://expected.supabase.co",
        supabase_jwks_url="https://expected.supabase.co/auth/v1/.well-known/jwks.json",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth,
        "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )
    expired = _signed_token(
        private_key,
        issuer="https://expected.supabase.co/auth/v1",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        auth._decode_token(expired)


def test_user_cannot_read_another_users_portfolio(client) -> None:
    created = client.post(
        "/api/v1/portfolios",
        json={"name": "Private", "currency": "USD"},
    )
    assert created.status_code == 201
    portfolio_id = created.json()["portfolio_id"]
    owner_view = client.get(f"/api/v1/portfolios/{portfolio_id}")
    assert owner_view.status_code == 200
    assert owner_view.json()["total_value"] == 0.0
    app.dependency_overrides[require_auth] = lambda: CurrentUser(
        user_id="different-user",
        email="other@example.com",
        role="INVESTOR",
    )

    denied = client.get(f"/api/v1/portfolios/{portfolio_id}/holdings")

    assert denied.status_code == 404
