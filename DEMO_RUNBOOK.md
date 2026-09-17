# Veyra Golden-Path Demo Runbook

This runbook validates the existing Veyra user journey without broker execution and without
replacing any quantitative component. The deterministic integration scenario uses the real
feature, GJR-GARCH, regime, signal, reliability, risk, optimizer, rebalance, paper-execution,
feedback, SQLAlchemy, and FastAPI code. Only the market-data provider and authenticated user are
deterministic test boundaries.

## 1. Prerequisites and configuration

Use Python 3.11, Node.js 20+, Docker, and Docker Compose. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
cp frontend/.env.example frontend/.env.local
npm --prefix frontend ci
python -m quant_engine.factors.setup
```

Populate placeholders locally; never commit either environment file.

Backend `.env` values needed for a real authenticated browser run:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_JWKS_URL=https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
CORS_ORIGINS=["http://localhost:5173"]
TRUSTED_HOSTS=["localhost","127.0.0.1"]
MARKET_DATA_PROVIDER=yfinance
MARKET_DATA_SECONDARY_PROVIDER=alpha_vantage
ALPHA_VANTAGE_API_KEY=YOUR_OPTIONAL_KEY
MARKET_DATA_FALLBACK_PROVIDER=yahoo_chart
FAMA_FRENCH_DATA_PATH=data/fama_french/F-F_Research_Data_5_Factors_2x3_daily.csv
```

Frontend `frontend/.env.local` values:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_SUPABASE_URL=https://PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY
```

Never put the database password, Supabase service-role/secret key, or a backend API key in a
`VITE_` variable.

Apply migrations and start both applications:

```bash
alembic upgrade head
uvicorn backend.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

Open `http://localhost:5173`.

## 2. Test account and browser portfolio

1. Open **Sign Up**, enter a name, an email you control, and a password of at least eight
   characters.
2. If Supabase email confirmation is enabled, use the confirmation email, then return to
   **Sign In**. The application never handles or stores the password itself.
3. Sign in. The frontend obtains `session.access_token` from Supabase and sends it as
   `Authorization: Bearer <JWT>` to Veyra. The backend verifies the JWKS signature, issuer,
   audience, expiry, and `sub` claim.
4. A new user is routed to **Onboarding**. Create `Golden Browser Demo`, currency `USD`, and add
   three liquid provider-supported holdings such as AAPL, MSFT, and SPY. Use a deliberately
   concentrated starting allocation if a rebalance recommendation is desired.
5. Finish onboarding and confirm that **Dashboard** and **Portfolio** display the persisted
   portfolio and holdings.

Real-provider outputs vary by market date. The exact reference outputs below belong to the
network-free deterministic scenario, not to AAPL/MSFT/SPY.

## 3. Deterministic seed and market scenario

The reproducible scenario lives in
`tests/integration/golden_scenario.py`:

- Portfolio: `Golden Demo`, owned by `test-user`, currency USD.
- Assets: AAA, BBB, CCC.
- Holdings: 80 AAA, 10 BBB, 10 CCC at deterministic 2025-09-10 closes.
- Market history: daily 2024-01-01 through 2025-09-11.
- Returns: deterministic drift plus two fixed sine cycles; no randomness or network access.
- OHLCV: positive, chronologically ordered, valid high/low relationships, increasing volume.
- First evaluation: 2025-09-10.
- Feedback-aware second evaluation: 2025-09-11.

Run it with:

```bash
pytest tests/integration/test_golden_user_journey.py -v
```

Expected reference outputs (minor optimizer floating-point tolerance applies):

| Output | Expected |
| --- | ---: |
| Initial regime threshold | 1.7806397407 |
| Initial regime | `HIGH_STRESS` |
| Composite risk | 0.1721326187 |
| Recommendation | `REBALANCE_REQUIRED` |
| Target AAA / BBB / CCC | 0.400000 / 0.400000 / 0.200000 |
| Turnover | 0.3682338179 |
| Filled paper orders | 3 |
| Feedback observed volatility | 0.0045982136 |
| Feedback updated threshold | 1.0000000000 |
| Second evaluation threshold | 1.0000000000 |
| Second regime | `HIGH_STRESS` |

The feedback threshold reaches the existing controller's configured upper bound. The key cycle
assertion is exact: the second persisted regime uses the first cycle's `updated_threshold`.

## 4. Journey audit

| Step | Frontend action and reflected state | API/auth and ownership | Service / quant path | Persisted state |
| --- | --- | --- | --- | --- |
| Signup | **Sign Up** calls `supabase.auth.signUp`; confirmation screen or onboarding follows | Supabase Auth request; no Veyra API route | Supabase Auth | Supabase `auth.users`; no password enters Veyra |
| Login | **Sign In** calls `signInWithPassword`, restores the session, lists owned portfolios, then routes to onboarding or dashboard | `GET /api/v1/portfolios` with Bearer JWT; `sub` scopes the list | `PortfolioService.list_portfolios_for_user` | Read-only; selected portfolio ID is stored in browser local storage |
| Onboarding | Profile → Portfolio → Holdings → Finish | Every Veyra request carries the same verified JWT | Existing portfolio and holding services | Portfolio gets JWT `sub` as `user_id`; holdings and weights are committed |
| Portfolio creation | Submit name/currency | `POST /api/v1/portfolios` | `PortfolioService.create_portfolio` | `portfolios` row; dashboard fetches it back |
| Holdings | Add each ticker/quantity/price | `POST /api/v1/portfolios/{id}/holdings`; owner mismatch is 404 | `PortfolioService.add_holding` and weight recalculation | `holdings`, `portfolio.total_value`, normalized weights; Portfolio screen refetches |
| Evaluation | Click **Evaluate Portfolio** / **Analyse Now** | `POST /api/v1/portfolios/{id}/signals/evaluate`; authenticated owner required | Historical market data → returns → GJR-GARCH → stress/regime → Phase 2 factors → base signal → reliability/risk → state-coupled control → constrained optimizer | `evaluations`, `volatility_states`, `regime_states`; final HOLD/REBALANCE decision is saved; UI stores the returned decision payload and history refetches |
| Portfolio control | Review regime, risk, reliability, controlled signals, and target deltas | Included in the evaluation response; no low-level math endpoint | `SignalRegulator`, `ReliabilityService`, `CompositeRiskService`, `StateCoupledControl`, `PortfolioOptimizer`, `TargetAllocator` | Correlated to the persisted `evaluation_id`; frontend renders server-computed math |
| Rebalance recommendation | Open **Rebalance Review** | No mutation while reviewing | Existing target allocator output | No new write; recommendation remains tied to `evaluation_id` |
| Approval | Click **Approve & Simulate** | `POST /api/v1/portfolios/{id}/rebalance` with `evaluation_id`, matching `as_of_date`, and literal `approved: true`; missing/false approval is 422; owner required | `RebalanceService` resolves the reviewed evaluation before planning | Execution cannot silently switch to a new evaluation ID |
| Paper execution | Review filled BUY/SELL orders; banner explicitly says no real trades | Same approved request | `RebalancePlanner` → `PaperExecutor` | `rebalance_events`, `trades`, and a separate `portfolio_snapshots` row; live holdings are intentionally untouched |
| Feedback | Rebalance page and Analytics show previous, observed, and updated threshold | `GET /api/v1/portfolios/{id}/feedback`; owner required | Existing `FeedbackService` | `feedback_updates`; frontend query is invalidated and refetched after execution |
| Subsequent evaluation | Run another evaluation on a later date | Same authenticated evaluation route | Latest feedback strictly earlier than the new as-of date selects the existing fixed-threshold compatibility strategy; all market inputs remain as-of bounded | New evaluation/volatility/regime rows; its `adaptive_threshold` equals the prior feedback update |

## 5. Expected API sequence

All `/api/v1` calls below include `Authorization: Bearer <Supabase access token>`.

```text
GET  /api/v1/portfolios                                      -> 200
POST /api/v1/portfolios                                      -> 201
POST /api/v1/portfolios/{portfolio_id}/holdings              -> 201 (per holding)
GET  /api/v1/portfolios/{portfolio_id}/holdings              -> 200
POST /api/v1/portfolios/{portfolio_id}/signals/evaluate      -> 201
GET  /api/v1/portfolios/{portfolio_id}/evaluations           -> 200
POST /api/v1/portfolios/{portfolio_id}/rebalance             -> 201
GET  /api/v1/portfolios/{portfolio_id}/feedback              -> 200
POST /api/v1/portfolios/{portfolio_id}/signals/evaluate      -> 201 (later date)
```

Approved paper execution request:

```json
{
  "as_of_date": "2025-09-10",
  "evaluation_id": "<the reviewed evaluation_id>",
  "approved": true
}
```

## 6. Expected screens

- **Sign Up**: account form, then confirmation instructions when email confirmation is enabled.
- **Sign In**: authenticated redirect to Onboarding for a first-time user.
- **Onboarding**: Profile, Portfolio, Holdings, Finish steps.
- **Dashboard / Portfolio**: persisted name, total value, holdings, and normalized allocation.
- **Evaluation**: market regime, volatility, composite risk, reliability, decision, current/target
  allocations, and estimated turnover.
- **Rebalance Review**: Analyse Portfolio → Review Recommendation → Approve & Simulate.
- **Executed state**: filled paper orders, simulated cost, explicit no-live-trades notice, and the
  persisted adaptive-threshold update.
- **Analytics**: latest feedback values and evaluation history from backend persistence.
- **Next Evaluation**: a new evaluation ID and a regime threshold seeded from the prior feedback
  cycle when its as-of date is later.

## 7. Full verification commands

```bash
pytest -q
npm --prefix frontend run lint
npm --prefix frontend run build
mypy backend config database quant_engine tests
ruff check backend config database quant_engine tests
python -m compileall backend config database quant_engine tests
git diff --check
docker build -t veyra-api:golden .
docker compose build
docker compose up -d
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
docker compose down
```

For a truly fresh migration check, point `DATABASE_URL` at an empty disposable PostgreSQL
database, run `alembic upgrade head`, and verify `alembic current`. Never reset or drop a shared
Supabase database for this test.
