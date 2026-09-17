"""Contract check for Supabase session forwarding in the browser API client."""

import subprocess
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


def test_frontend_auth_handles_confirmation_recovery_and_safe_errors() -> None:
    root = Path(__file__).parents[2] / "frontend/src"
    context = (root / "auth/auth-context.tsx").read_text()
    signup = (root / "pages/sign-up-page.tsx").read_text()
    errors = (root / "auth/auth-errors.ts").read_text()
    router = (root / "app/router.tsx").read_text()

    assert 'return "confirmation_required"' in context
    assert "supabase.auth.resend" in context
    assert "supabase.auth.updateUser" in context
    assert 'redirectTo: `${window.location.origin}/reset-password`' in context
    assert "setResendCooldown(60)" in signup
    assert "Too many verification emails were requested" in errors
    assert 'path: "/reset-password"' in router


def test_local_environment_files_are_ignored_and_tokens_are_not_logged() -> None:
    root = Path(__file__).parents[2]
    ignored = subprocess.run(
        ["git", "check-ignore", "frontend/.env.local"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    client_source = (root / "frontend/src/api/client.ts").read_text()

    assert ignored.returncode == 0
    assert "console.log" not in client_source
    assert "console.debug" not in client_source
