# Veyra deployment

Veyra uses Supabase Auth in the browser and verifies Supabase access tokens in FastAPI.
The backend does not need, accept, or expose a Supabase service-role key for current flows.

## Environments

### Local

Copy `.env.example` to `.env` and `frontend/.env.example` to `frontend/.env.local`.
SQLite is suitable for tests. Local application development can use the Compose PostgreSQL profile.
The authentication bypass is off by default. To use its deterministic local identity, both
`APP_ENV=development`, `LOCAL_DEVELOPMENT=true`, and `AUTH_BYPASS_ENABLED=true` are required.

```bash
docker compose --profile local-dev up --build
```

### Staging

Use a separate Supabase project and database. Set `APP_ENV=staging`, explicit CORS origins and
trusted hosts, and keep both local-auth flags false. Staging refuses to start if bypass is enabled
or Supabase JWT verification is incomplete.

### Production

Required backend variables:

- `APP_ENV=production`
- `DATABASE_URL`: PostgreSQL/Supabase URL; use `sslmode=require` where required
- `SUPABASE_URL`: project URL used to validate the JWT issuer
- `SUPABASE_JWKS_URL`: project JWKS endpoint
- `SUPABASE_JWT_AUDIENCE`: normally `authenticated`
- `CORS_ORIGINS`: JSON list containing only deployed frontend origins
- `TRUSTED_HOSTS`: JSON list containing only deployed API hostnames
- `LOG_LEVEL` and `STRUCTURED_JSON_LOGS`

Optional operational variables are documented in `.env.example`: database pool sizing, market-data
provider/retry/cache settings, the Alpha Vantage key, scheduler settings, and the Fama-French path.
Keep `AUTH_BYPASS_ENABLED=false` and `LOCAL_DEVELOPMENT=false` in production.

Required frontend build variables:

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY` (the browser-safe publishable key)

Never put `DATABASE_URL`, a service-role key, provider secret, or another backend credential in a
`VITE_` variable.

## Release commands

Run migrations as a one-off release task before replacing application instances:

```bash
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Build the frontend with its three public build variables, then serve `frontend/dist` from a CDN or
the included unprivileged nginx image. The Compose stack builds both images:

```bash
docker compose build
docker compose up -d
```

`GET /health` is a process liveness check. `GET /ready` checks database connectivity and that the
database revision equals the checked-in Alembic head. Both endpoints are deliberately public and
cheap. `/api/v1/system/status` is admin-authenticated.

## Authentication and email

The browser restores one Supabase session and sends its access token as `Authorization: Bearer`.
FastAPI verifies the JWKS signature, issuer, audience, expiry, and subject. Portfolio ownership is
matched to that verified subject. Signup supports both immediate sessions and confirmation-required
projects. Supabase hosted email delivery can impose development rate limits; configure custom SMTP
for production rather than disabling email verification. The client resend cooldown improves UX but
does not replace provider-side limits.

Admin role claims are read only from Supabase `app_metadata`, never user-editable `user_metadata`.
Provision administrators through a trusted Supabase administrative workflow.

## Scheduler and rate limits

`SCHEDULER_ENABLED` defaults to false. Run exactly one scheduler-enabled application process (or a
dedicated scheduler deployment); leave it false on other web workers. Database run claims make jobs
idempotent, but multiple embedded schedulers still create avoidable contention.

Veyra has no distributed application rate limiter. Configure edge/API-gateway limits for signup and
login at Supabase, and for evaluation, optimization, upload, and backtest endpoints at the API edge.
Do not rely on an in-memory limiter in a multi-worker deployment.

## Deployment checks

```bash
alembic heads
alembic current
pytest tests/ -v
python -m compileall backend config database quant_engine tests
ruff check backend config database quant_engine tests
cd frontend && npm ci && npm run lint && npm run build
```
