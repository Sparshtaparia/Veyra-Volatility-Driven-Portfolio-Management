# Phase 6 — Production operations

Phase 6 wraps the completed Veyra quant engine with operational controls. It
does not change volatility, factor, reliability, risk, state-coupling,
optimization, feedback, or backtest formulas, and it never sends broker orders.

## Runtime architecture

```text
APScheduler cron trigger
  → enumerate portfolios
  → atomically claim scheduled_runs key (run type, portfolio, date)
  → deterministic evaluation_id
  → volatility and regime
  → features, factors, reliability, risk, controlled signals
  → portfolio optimization and paper rebalance
  → existing Phase 3–5 persistence
  → complete scheduled_runs with timings
```

Full evaluation and volatility-only refreshes have independent run types and
cron schedules. APScheduler coalesces missed triggers and permits one local
instance of each job. The database uniqueness constraint is the cross-process
guard, so multiple API workers cannot complete the same portfolio/date job.
Failed and expired `RUNNING` claims are safely reclaimable; completed runs are
never repeated.

Analytical services retain their existing stage-level transactions. A failed
later stage can be resumed with the deterministic evaluation ID rather than
duplicating earlier rows. The operational ledger records failure type, bounded
error text, provider, timestamps, total duration, and per-stage duration.

## Market data

`ResilientMarketDataProvider` implements the existing `MarketDataProvider`
interface and adds:

- bounded exponential retries;
- provider timeouts;
- request-rate throttling and bounded `Retry-After` handling;
- configurable fallback provider;
- empty/stale-data rejection;
- an in-memory TTL cache scoped to the exact ticker/start/end request;
- provider provenance and structured attempt logs.

Cached observations are immutable validated domain bars. Exact request keys and
date filtering prevent a wider or newer request from satisfying a historical
evaluation. The volatility service additionally drops every bar after the
evaluation date, even if an upstream provider violates its date contract.

The provider registry supports `yfinance` and the direct `yahoo_chart` adapter.
The latter is the default fallback and can be replaced without changing any
quant service.

## Configuration and Supabase

Production startup validation requires:

- a PostgreSQL SQLAlchemy `DATABASE_URL`;
- a `VEYRA_API_KEY` of at least 32 characters;
- explicit CORS origins and trusted hosts;
- a Fama-French data path when scheduled full evaluations are enabled.

For Supabase, use its direct or session-pooler PostgreSQL URI with
`postgresql+psycopg2://` and `sslmode=require`. Credentials remain server-side.
The SQLAlchemy engine enables `pool_pre_ping`, bounded pool/overflow sizes,
timeouts, LIFO reuse, and connection recycling. Configure pool size relative to
the Supabase plan and the number of API replicas.

Run migrations before application startup:

```bash
alembic upgrade head
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Readiness requires both a successful `SELECT 1` and Alembic revision
`0004_phase6_operations`.

## Security and observability

All `/api/v1/*` routes require `X-API-Key` when `VEYRA_API_KEY` is configured.
Health endpoints remain unauthenticated for orchestrators. Trusted-host, CORS,
constant-time key comparison, request IDs, no-store, anti-sniffing, frame, and
referrer headers provide baseline API hardening. Production OpenAPI/ReDoc pages
are disabled.

Logs are JSON by default and include run/evaluation/portfolio IDs, provider,
evaluation date, status, duration, stage timings, request ID, and failures.
The process-local metrics registry exposes counters and duration summaries via
the authenticated system-status endpoint. `error_monitor.register(callback)`
is a vendor-neutral hook for Sentry or another external reporter.

Operational endpoints:

- `GET /health` — backward-compatible liveness alias
- `GET /health/live` — process liveness
- `GET /health/ready` — database and migration readiness
- `GET /api/v1/system/status` — scheduler, provider/cache, run, and timing state
- `GET /api/v1/portfolios/{portfolio_id}/evaluations` — persisted history

## Deployment

The backend container runs as a non-root user. Compose drops Linux capabilities,
enables `no-new-privileges`, uses a read-only root filesystem with a bounded
`/tmp`, initializes PID 1, applies health checks, and provides a graceful stop
window. The container command upgrades Alembic before starting the API.

For multiple replicas, run the embedded scheduler in only the intended workers
when practical. Database claims make duplicate analytical execution safe, but a
dedicated scheduler process provides cleaner ownership at larger scale.

## Limitations

- The operational metrics registry is process-local; production fleets should
  export it to a shared metrics backend.
- APScheduler uses an in-memory schedule. The database ledger protects runs,
  but the cron definitions themselves are supplied through environment config.
- Both built-in adapters currently use Yahoo as the upstream source. True vendor
  diversification requires an additional licensed market-data adapter.
- Threads enforce caller-visible timeouts but cannot forcibly terminate a
  blocking third-party function already executing in Python.
- API-key authentication is a deployment baseline, not per-user RBAC or OAuth.
- There is no live brokerage or automatic external order execution.
