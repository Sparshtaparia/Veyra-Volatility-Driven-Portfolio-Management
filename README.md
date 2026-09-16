# Veyra — Volatility-Driven Portfolio Management

Veyra is a portfolio-control platform for people who already invest. It helps answer one practical question:

> Does my existing portfolio need attention as market conditions change?

Veyra is not a stock-discovery product and does not execute real trades. It records portfolios, evaluates their state, and presents results in plain language. Rebalancing is deliberately a review-and-approval workflow; paper execution is enabled only when the backend provides a verified proposal and execution API.

## Features

### Investor application

- Responsive welcome page and beginner-friendly onboarding
- Sign-up, sign-in, and password-reset UI
- Portfolio creation and existing-holding entry
- Portfolio summary, holdings table, and allocation chart
- Manual portfolio evaluation and result retrieval
- Activity timeline built from real saved portfolio/evaluation context
- Rebalance review that keeps approval disabled until a real proposal exists
- Accessible loading, empty, error, forbidden, and not-found states
- Desktop sidebar, mobile navigation, and route-level code splitting

### Admin application

- Role-aware admin route and responsive admin shell foundation
- Development-only demo admin account
- Admin health integration is being prepared; operational user/audit data needs protected backend endpoints

### Backend and quant engine

- FastAPI API, Pydantic schemas, SQLAlchemy, Alembic migrations
- PostgreSQL/Supabase-compatible configuration
- Portfolio, holdings, and evaluation persistence
- Market feature, volatility-evaluation, and market-regime routes
- GJR-GARCH volatility/regime engine plus Phase 4 intelligence and Phase 5 control modules

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite |
| UI | Tailwind CSS, shadcn/ui foundations, Lucide |
| Client data | TanStack Query |
| Tables and charts | TanStack Table, Recharts, Plotly |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| Persistence | SQLAlchemy 2.x, Alembic, PostgreSQL / Supabase PostgreSQL |
| Quant engine | Python, GJR-GARCH volatility and regime modules |
| Testing | pytest |

## Architecture

```text
React + TypeScript UI
         │
Centralized frontend API client
         │
      FastAPI API
         │
Portfolio/evaluation services
         │
Quant engine + PostgreSQL
```

```text
Existing portfolio → Add holdings → Evaluate → Display decision
                                          │
                         Review real rebalance proposal when available
                                          │
                     Explicit paper-execution approval in a future phase
```

## Project structure

```text
├── frontend/                 # React + Vite application
│   └── src/
│       ├── api/              # Centralized API clients
│       ├── app/              # Router
│       ├── auth/             # Demo auth and role guards
│       ├── components/       # Shared UI and layouts
│       ├── hooks/            # TanStack Query hooks
│       └── pages/            # Public, investor, admin pages
├── backend/                  # FastAPI routes, services, schemas
├── config/                   # Application settings
├── database/                 # Models and repositories
├── quant_engine/             # Features, volatility, regimes, control
├── migrations/               # Alembic migrations
├── tests/                    # Backend tests
├── .env.example
└── requirements.txt
```

## Prerequisites

- Node.js 20+ recommended
- Python 3.10+
- PostgreSQL or a Supabase PostgreSQL project
- Git

## Environment configuration

Create a root `.env`:

```powershell
Copy-Item .env.example .env
```

Configure at least:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
APP_ENV=development
LOG_LEVEL=INFO
API_PREFIX=/api/v1
DEFAULT_CURRENCY=INR
```

Create the frontend environment file:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Never commit environment files, database passwords, service-role keys, or private API credentials.

## Local development

### Backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Health check: `http://127.0.0.1:8000/health`

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:5173`.

Production build:

```powershell
cd frontend
npm run build
```

## Routes

| Area | Route | Purpose |
| --- | --- | --- |
| Public | `/` | Welcome page |
| Public | `/sign-up` | Account-creation UI |
| Public | `/sign-in` | Sign-in UI |
| Public | `/forgot-password` | Password-reset request UI |
| Investor | `/app` | Portfolio dashboard |
| Investor | `/app/rebalance` | Rebalance review |
| Investor | `/app/activity` | Current activity timeline |
| Admin | `/admin` | Admin console foundation |
| Shared | `/403` | Access-restricted page |
| Shared | `*` | Not-found page |

## Demo authentication

Current role handling is a frontend-only development mock, not production authentication.

| Role | Credential | Destination |
| --- | --- | --- |
| Admin | `admin@gmail.com` / `admin` | `/admin` |
| Investor | Any valid-looking email with a non-empty password | `/app` |

There is no email verification, OTP, real password reset, or backend-enforced authorization in the current demo flow. Replace mock auth with protected backend authentication before deployment.

## Available API endpoints

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | API health status |
| POST | `/api/v1/portfolios` | Create portfolio |
| GET | `/api/v1/portfolios/{portfolio_id}` | Retrieve portfolio |
| GET | `/api/v1/portfolios/{portfolio_id}/holdings` | List holdings |
| POST | `/api/v1/portfolios/{portfolio_id}/holdings` | Add holding |
| POST | `/api/v1/portfolios/{portfolio_id}/evaluate` | Create evaluation |
| GET | `/api/v1/portfolios/{portfolio_id}/evaluations/{evaluation_id}` | Retrieve evaluation |
| GET | `/api/v1/portfolios/{portfolio_id}/features` | Retrieve market features |
| POST | `/api/v1/portfolios/{portfolio_id}/volatility/evaluate` | Persist volatility evaluation |
| GET | `/api/v1/evaluations/{evaluation_id}/volatility` | Retrieve volatility output |
| GET | `/api/v1/evaluations/{evaluation_id}/regime` | Retrieve market regime |
| GET | `/api/v1/portfolios/{portfolio_id}/regime/latest` | Retrieve latest regime |

### Create portfolio

```bash
curl -X POST http://127.0.0.1:8000/api/v1/portfolios \
  -H "Content-Type: application/json" \
  -d '{"name":"My Portfolio","currency":"INR"}'
```

### Add holding

```bash
curl -X POST http://127.0.0.1:8000/api/v1/portfolios/PORTFOLIO_ID/holdings \
  -H "Content-Type: application/json" \
  -d '{"ticker":"TCS","quantity":20,"average_price":3500,"current_price":3600}'
```

### Evaluate portfolio

```bash
curl -X POST http://127.0.0.1:8000/api/v1/portfolios/PORTFOLIO_ID/evaluate \
  -H "Content-Type: application/json" \
  -d '{"evaluation_date":"2026-09-16","trigger":"MANUAL"}'
```

## Current limitations

The frontend intentionally does not fake results for unavailable backend capabilities:

- Authentication, registration, reset-password, and role APIs
- Admin users, metrics, evaluation-list, and audit-log APIs
- Portfolio-list and full activity-history APIs
- Target-allocation / optimizer / rebalance-proposal API
- Paper-execution and execution-feedback APIs

Therefore, evaluation is not rebalancing, no trade is automatic, rebalance approval remains disabled, and admin data cannot be presented as production data until protected API endpoints exist.

## Development roadmap

| Phase | Status | Scope |
| --- | --- | --- |
| 1 | Complete | Project foundation |
| 2 | Complete | Local workflow |
| 3 | Complete | Public welcome page and routing |
| 4 | Complete | Auth UI and demo roles |
| 5 | Complete | Investor dashboard and portfolio APIs |
| 6 | Complete | Rebalance review UI; proposal API pending |
| 7 | Complete | Activity UI; execution/feedback APIs pending |
| 8 | Complete | Code splitting, loading, 403, and 404 polish |
| 9 | In progress | Responsive admin console and health integration |

## Testing

```powershell
# Backend tests
pytest tests/ -v

# Backend syntax check
python -m compileall -q backend config database

# Frontend build
cd frontend
npm run build
```

## Product and security principles

- Investments are subject to market risk.
- Veyra provides portfolio-control insights; it does not guarantee returns.
- Route guards improve user experience but are not a security boundary.
- Backend authorization must be implemented before production use.
- Quantitative calculations and trade logic stay in the backend/quant engine, never in UI components.

## License

This repository is currently maintained as an academic/product prototype. Add an explicit license before public production distribution.
