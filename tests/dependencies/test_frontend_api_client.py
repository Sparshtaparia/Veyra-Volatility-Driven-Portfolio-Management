"""Contract check for Supabase session forwarding in the browser API client."""

from pathlib import Path


def test_frontend_api_client_forwards_the_supabase_access_token() -> None:
    source = (Path(__file__).parents[2] / "frontend/src/api/client.ts").read_text()
    assert "supabase.auth.getSession()" in source
    assert "session?.access_token" in source
    assert "`Bearer ${session.access_token}`" in source
    assert "new Headers(options.headers)" in source
    assert '!headers.has("Authorization")' in source
    assert "VITE_SUPABASE_SERVICE_ROLE_KEY" not in source
    assert "VITE_VEYRA_API_KEY" not in source


def test_frontend_login_uses_the_shared_supabase_client() -> None:
    root = Path(__file__).parents[2] / "frontend/src"
    auth_source = (root / "auth/auth-context.tsx").read_text()
    supabase_source = (root / "lib/supabase.ts").read_text()
    assert "supabase.auth.signInWithPassword" in auth_source
    assert "supabase.auth.signUp" in auth_source
    assert "supabase.auth.onAuthStateChange" in auth_source
    assert "demoAdmin" not in auth_source
    assert sum("createClient(" in path.read_text() for path in root.rglob("*.ts*")) == 1
    assert "persistSession: true" in supabase_source
