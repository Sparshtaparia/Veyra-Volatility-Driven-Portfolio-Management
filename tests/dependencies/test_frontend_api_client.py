"""Contract check for Supabase session forwarding in the browser API client."""

from pathlib import Path


def test_frontend_api_client_forwards_the_supabase_access_token() -> None:
    source = (Path(__file__).parents[2] / "frontend/src/api/client.ts").read_text()
    assert "supabase.auth.getSession()" in source
    assert "Authorization: `Bearer ${data.session.access_token}`" in source
    assert "VITE_SUPABASE_SERVICE_ROLE_KEY" not in source
    assert "VITE_VEYRA_API_KEY" not in source
