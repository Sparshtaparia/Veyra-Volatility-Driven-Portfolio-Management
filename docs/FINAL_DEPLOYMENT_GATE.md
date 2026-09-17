# Veyra final deployment gate

Validation date: 2026-09-17

## 1. Commit and repository state tested

- Branch: `main`
- Commit: `be32bf3`
- The existing working tree was intentionally dirty when this continuation began. It was inspected
  with `git status --short` and protected; no existing changes were reset, checked out, or discarded.
- `git diff --check` passed before deployment work and after the final changes.

## 2. Fresh PostgreSQL result

- PostgreSQL `15.19` (`postgres:15-alpine`) was started as an isolated, empty database.
- `alembic upgrade head` completed from an empty schema without `create_all` or seed data.
- The resulting public schema contains 20 expected tables, 27 foreign keys, 52 indexes, and 328
  primary-key, unique, check, and foreign-key constraints.
- Missing expected tables: none. Unexpected tables: none.

## 3. Alembic result

- Linear chain applied: `0000_phase1_baseline` -> `0001_phase3_volatility_regime` ->
  `0002_phase4_intelligence` -> `0003_phase5_portfolio_control` ->
  `0004_phase6_operations` -> `0005_supabase_auth`.
- `alembic current`: `0005_supabase_auth (head)`.
- `alembic heads`: `0005_supabase_auth (head)`.
- Readiness derives the expected revision from the checked-in Alembic graph rather than a stale
  hard-coded revision.

## 4. Backend Docker build result

- `docker build -t veyra-backend:test .` passed on Python 3.11 slim.
- Native dependencies build successfully using a temporary build toolchain that is purged afterward.
- The runtime image includes the required `execution` package and imports `backend.main` successfully.
- The image runs as non-root user `veyra`. `.env` and tests are absent from the image.
- No local-machine-only path is required.

## 5. Frontend Docker build result

- The Node 20 `npm ci` and production Vite build stages passed.
- The unprivileged nginx runtime stage built successfully.
- `frontend/.dockerignore` excludes local environment files, `node_modules`, and build output.
- Only browser-public `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and
  `VITE_SUPABASE_ANON_KEY` are build inputs.

## 6. Compose startup result

- `docker compose config --quiet`, `docker compose build`, and `docker compose up -d` passed using
  disposable development values and the local PostgreSQL 15 profile.
- PostgreSQL became healthy, the API became healthy after applying all migrations, and the frontend
  started successfully.
- The Compose API now forwards the config-driven `SUPABASE_JWT_AUDIENCE` setting.

## 7. Health probe results

| Probe | Result |
|---|---:|
| `GET /health` | 200, `live` |
| `GET /ready` | 200, database connected, schema current |
| `GET /health/ready` | 200, database connected, schema current |

Readiness executed a database query and compared the database revision with the current Alembic
head (`0005_supabase_auth`); it was not merely a process-listening check.

## 8. Frontend smoke result

- `/`: 200.
- Built JavaScript asset: 200 (1,061,068 bytes).
- `/sign-in`: 200 and returned the SPA entry document through nginx fallback.
- `/healthz`: 200.
- `/api/v1/system/status` proxied to the API and returned the expected unauthenticated 401.
- The built bundle contains the configured public API/Supabase values and no PostgreSQL URL.

## 9. Authentication production-safety result

- A production settings instance with `AUTH_BYPASS_ENABLED=true` was rejected.
- The running Compose API had `AUTH_BYPASS_ENABLED=false` and `LOCAL_DEVELOPMENT=false`.
- `SUPABASE_URL`, `SUPABASE_JWKS_URL`, and `SUPABASE_JWT_AUDIENCE` remain environment-driven.
- No tokens, credentials, or database URLs were printed during verification.

## 10. Database SSL configuration result

- Production configuration accepts PostgreSQL and rejects SQLite.
- A Supabase PostgreSQL URL without `sslmode=require` was rejected.
- The real production/Supabase URL was neither required for the isolated test nor exposed.

## 11. Scheduler limitation

`SCHEDULER_ENABLED` defaults to false. Deploy exactly one scheduler-enabled application process (or
one dedicated scheduler deployment). Database run claims provide job idempotency, but the embedded
scheduler is not distributed and multiple enabled processes create avoidable contention.

## 12. Final automated test results

- Golden API journey after Compose startup: 1 passed.
- Full backend suite: 207 passed, 1 dependency deprecation warning.
- MyPy: success in 137 production source files.
- Ruff: all checks passed.
- Python 3.11 compileall: passed.
- Frontend ESLint: passed.
- Frontend TypeScript/Vite production build: passed.
- `git diff --check`: passed.

The 207-test baseline did not change.

## 13. Remaining warnings

- Starlette imports the legacy `multipart` module name and emits one upstream pending-deprecation
  warning.
- Vite reports a JavaScript chunk over 500 kB (approximately 1.06 MB, 304 kB gzip).
- Docker's build scanner labels the browser-public Supabase anon-key build argument as a possible
  secret. This key is intentionally public and is embedded in every Supabase browser application;
  service-role and backend credentials are not frontend build inputs.

## 14. Remaining operational risks

- Real Supabase connectivity, deployed DNS/TLS, production secrets, email delivery, and provider
  quotas require environment-specific release validation.
- The golden API journey ran through the real deterministic quant pipeline in the host test process
  after containers started. It was not repeated inside the production-auth Compose container because
  no real Supabase JWT or live provider credentials were supplied.
- Market-data providers remain external dependencies; production monitoring and configured fallback
  credentials are required.
- Run database migrations as a one-off release task before scaling application instances.
- The scheduler must remain enabled in only one process.

## 15. GO / NO-GO verdict

**GO for deployment**, conditional on supplying the documented production Supabase/database values,
deployed CORS/host values, and any desired provider credentials through the deployment secret store.
All repository-controlled acceptance gates passed; no live brokerage or real order execution was
performed.
