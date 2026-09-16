# Veyra — Volatility-Driven Portfolio Management

> **Your portfolio doesn't need to be rebuilt every day. Veyra tells you when it needs to change.**

Veyra is a quantitative portfolio-management and allocation-control system that monitors an **existing portfolio**, evaluates changing market conditions, and determines whether portfolio allocation should adapt.

Unlike a conventional stock-discovery application, Veyra starts with the investor's current portfolio and evaluates whether the portfolio's allocation should be maintained or changed.

---

## 1. What is Veyra?

Veyra is built around a closed-loop, volatility-driven portfolio control architecture.

The system combines:

- Market-derived features
- Base signal generation
- Conditional volatility estimation
- Volatility regime detection
- Signal orientation and attenuation
- Asset-level signal reliability
- Portfolio-level composite risk
- State-coupled control
- Constrained allocation optimization
- Rebalancing
- Portfolio outcome monitoring
- Adaptive feedback

The technical architecture is based on the invention:

**“A System and Method for Volatility-Driven Portfolio Allocation Control Using State-Coupled Signal Regulation.”**

The invention describes interconnected data acquisition, feature engineering, volatility estimation, regime control, signal regulation, risk-state generation, optimization/allocation, feedback stabilization, and execution/portfolio-update modules.

---

## 2. Core Product Idea

Veyra answers:

> **“Given my existing portfolio and the current market state, does my allocation need to change?”**

It does not treat every price movement as a reason to trade.

The system separates:

**Evaluation frequency** from **rebalancing frequency**.

An evaluation can conclude:

- `HOLD` — current allocation remains acceptable
- `REBALANCE` — target allocation differs sufficiently from the current portfolio

This allows Veyra to continuously evaluate portfolio conditions without unnecessarily generating trades.

---

## 3. Core Control Loop

```text
EXISTING PORTFOLIO
        │
        ▼
MARKET MONITOR
        │
        ▼
FEATURE ENGINEERING
        │
        ▼
BASE SIGNAL
        │
        ▼
VOLATILITY / REGIME
        │
        ▼
SIGNAL REGULATION
        │
        ├───────────────┐
        ▼               ▼
RELIABILITY       COMPOSITE RISK
        │               │
        └───────┬───────┘
                ▼
       STATE-COUPLED CONTROL
                │
                ▼
      TARGET ALLOCATION
                │
        CURRENT vs TARGET
                │
          ┌─────┴─────┐
          ▼           ▼
        HOLD      REBALANCE
                      │
                      ▼
             USER APPROVAL /
             PAPER EXECUTION
                      │
                      ▼
             UPDATED PORTFOLIO
                      │
                      ▼
             OUTCOME MONITOR
                      │
                      ▼
             FEEDBACK STATE
                      │
                      ▼
          NEXT EVALUATION CYCLE
```

The architecture is intentionally interdependent: volatility, risk, reliability, and signal state are passed into the state-coupled control stage rather than being treated as isolated analytical outputs.

---

## 4. Technical Architecture

```text
                         VEYRA
                           │
             ┌─────────────┴─────────────┐
             │                           │
         Next.js                     FastAPI
         Frontend                     Backend
             │                           │
             │                      Application
             │                       Services
             │                           │
             │                    ┌──────┴──────┐
             │                    │             │
             │                Database      Quant Engine
             │                Repositories
             │                    │             │
             └──────────────┐     │             │
                            │     │             │
                         Supabase PostgreSQL    │
                            │                   │
                            └─────────┬─────────┘
                                      │
                                Evaluation State
```

### Backend separation

```text
backend/
    API
      ↓
    Application Services
      ↓
    Domain / Quant Contracts
      ↓
database/
    SQLAlchemy Models
    Repositories
      ↓
Supabase PostgreSQL
```

The quant engine remains independent from database-specific implementation.

---

## 5. Quantitative Pipeline

### 5.1 Market Data

Market data is acquired through an abstract market-data provider.

The provider boundary allows the quantitative modules to remain independent of the underlying data source.

---

### 5.2 Feature Engineering

Current feature engineering includes market-derived technical and liquidity features such as:

- RSI
- ATR
- MACD Histogram
- Bollinger Band Width
- Dollar Volume

These features form inputs to the base signal layer and risk-related processing.

**Dollar Volume is treated as a liquidity/trading-activity proxy, not as a direct prediction of price movement.**

---

### 5.3 Base Signal

The base signal combines normalized market-derived information into an asset-level signal state.

The signal layer is deliberately separated from the later control layers.

Conceptually:

```text
Market Features
      ↓
Normalization
      ↓
Factor / Signal Inputs
      ↓
Base Signal
```

---

### 5.4 Volatility Estimation

Veyra uses asymmetric conditional volatility estimation based on **GJR-GARCH(1,1)**.

Conceptually:

```text
Market Returns
      ↓
GJR-GARCH
      ↓
Conditional Volatility
      ↓
Volatility State
```

The asymmetric specification allows negative shocks to affect conditional volatility differently from positive shocks.

---

### 5.5 Volatility Regime

Conditional volatility is compared with an adaptive threshold.

Conceptually:

```text
σt > θt  → HIGH_VOLATILITY
σt ≤ θt  → NORMAL
```

The threshold is derived from historical volatility behavior and is intended to adapt over time.

The regime state affects downstream signal interpretation and regulation.

---

### 5.6 Signal Regulation

Under elevated volatility, signal propagation can be attenuated.

The system therefore distinguishes:

```text
Base Signal
     ↓
Regime / Orientation
     ↓
Volatility Attenuation
     ↓
Effective Regulated Signal
```

This is intended to reduce unstable signal propagation during stressed conditions.

---

### 5.7 Reliability

Veyra generates an asset-level reliability state from asset-specific volatility.

A representative implementation is:

```text
W(i,t) = exp(-κ σ(i,t))
```

where:

- `W(i,t)` = reliability
- `κ` = sensitivity parameter
- `σ(i,t)` = asset-specific volatility

Reliability is bounded between 0 and 1 and decreases smoothly as instability increases.

Reliability represents confidence in the usefulness/stability of an asset's signal; it is distinct from portfolio-level risk.

---

### 5.8 Composite Risk

The portfolio-level risk state aggregates supported risk dimensions including:

- Volatility exposure
- Drawdown
- Liquidity stress
- Cross-asset correlation/concentration

The architecture also supports a nonlinear interaction between volatility and correlation to represent correlated volatility amplification during stressed states.

Conceptually:

```text
Volatility ───────┐
Drawdown ─────────┤
Liquidity ────────┼──→ Composite Risk State
Correlation ──────┤
Vol × Corr ───────┘
```

The implementation should use explicit normalization and configurable weighting rather than hidden or arbitrary transformations.

---

### 5.9 State-Coupled Control

The central control stage jointly consumes:

```text
Regulated Signal
Volatility State
Composite Risk State
Reliability State
        │
        ▼
State-Coupled Control Operator
        │
        ▼
Control Output
```

The objective is not simply to run independent:

```text
Signal → Risk → Optimizer
```

modules.

Instead, the downstream control behavior is coupled to the measured system state.

---

## 6. Allocation and Rebalancing

The allocation layer determines target portfolio weights subject to portfolio constraints.

A representative control objective incorporates:

- Expected return
- Portfolio risk
- Turnover
- Volatility penalties
- State-coupled risk/reliability penalties

Typical constraints include:

- Full investment
- Minimum/maximum asset weights
- Turnover limits
- Concentration constraints

The target allocation is then compared against the current allocation:

```text
Current Weights
      │
      ├──────────────┐
      │              │
      ▼              ▼
Current Portfolio   Target Portfolio
      │              │
      └──────┬───────┘
             ▼
       Allocation Delta
             │
             ▼
       HOLD / REBALANCE
```

The current implementation should keep execution separated from the decision engine. Paper execution can be used before broker-connected execution.

---

## 7. Adaptive Feedback

Veyra is designed as a closed-loop system.

After a portfolio update, realized behavior can be monitored through metrics such as:

- Realized volatility
- Drawdown deviation
- Allocation instability
- Turnover
- Signal stability

The feedback layer uses realized risk deviation to update the adaptive threshold for future evaluation cycles.

Conceptually:

```text
Evaluation
    ↓
Control
    ↓
Allocation
    ↓
Portfolio Update
    ↓
Realized Outcome
    ↓
Risk Deviation
    ↓
Adaptive Threshold Update
    ↓
Next Evaluation
```

This creates the feedback component of the Veyra control architecture.

---

## 8. Evaluation vs Rebalancing

These are intentionally different operations.

### Evaluation

Asks:

> What is the current state of the portfolio and market?

It produces information such as:

- Current volatility regime
- Reliability
- Composite risk
- Regulated signals
- State-coupled control output
- Target allocation
- HOLD / REBALANCE decision

### Rebalancing

Asks:

> Should the portfolio actually move from current weights toward target weights?

A trigger can initiate an evaluation without directly executing a trade.

---

## 9. Evaluation Triggers

Veyra can support several evaluation triggers:

### Periodic

Examples:

- Daily
- Weekly
- Monthly

### Manual

User selects:

**Evaluate Portfolio Now**

### Portfolio Change

Adding a new stock/holding can trigger a new portfolio evaluation.

### Price Threshold

A user can define a threshold such as:

```text
TCS moves ±10% from today's reference price
        ↓
Trigger evaluation / notification
```

The threshold event should not automatically imply trade execution.

---

## 10. User Roles

Veyra has two primary application roles.

### INVESTOR

Investor-facing capabilities include:

```text
Home
Portfolio
Evaluation / Decision Center
Triggers
Activity
Analytics
Settings
```

The investor experience focuses on:

> **What is happening to my portfolio, and does Veyra think it needs to change?**

### ADMIN

Administrative capabilities include:

```text
Admin Dashboard
Users
Evaluations
System
Audit
```

The admin experience focuses on:

> **What is happening across the Veyra system?**

Frontend role checks are for user experience; backend authorization remains the security boundary.

---

## 11. Supabase

Veyra uses **Supabase as its primary database platform**.

The Supabase project provides:

- PostgreSQL database
- Authentication
- Database infrastructure

Target architecture:

```text
Next.js
   │
   ├── Supabase Auth
   │       ↓
   │     JWT
   │       ↓
   │    FastAPI
   │
   └──────────────────┐
                      ▼
              Supabase PostgreSQL
                      ▲
                      │
                  SQLAlchemy
                      ▲
                      │
                   FastAPI
```

### Database

Veyra's application data is stored in the PostgreSQL database provided by Supabase.

The backend uses SQLAlchemy/repositories to access the database.

### Authentication

Supabase Auth provides user authentication.

The backend validates authenticated requests and applies Veyra's investor/admin authorization rules.

### Environment variables

Backend:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWKS_URL=
DATABASE_URL=
VEYRA_API_KEY=
CORS_ORIGINS=["https://app.example.com"]
TRUSTED_HOSTS=["api.example.com"]
```

`VEYRA_API_KEY` is the API-key authentication option when Supabase Auth is
not configured; production requires it to be at least 32 characters. Use
`CORS_ORIGINS` (not `FRONTEND_ORIGINS`) and `TRUSTED_HOSTS` to specify explicit
production domains. Keep the database URL and all Supabase/service-role keys
backend-only.

Frontend:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

The service-role/secret key must remain backend-only.

### Local Fama-French data

Phase 4 reads decimal daily five-factor returns from the repo-relative path
`data/fama_french/F-F_Research_Data_5_Factors_2x3_daily.csv` by default. Fetch
and validate the official Ken French daily dataset once for local development:

```bash
python -m quant_engine.factors.setup
```

The utility caches the file locally and validates dates plus `Mkt-RF`, `SMB`,
`HML`, `RMW`, `CMA`, and `RF`; it does not create synthetic factor data. Set
`FAMA_FRENCH_DATA_PATH` only to override that location.

### Market-data fallback

The normal order is `yfinance → alpha_vantage → yahoo_chart`. Alpha Vantage is
independent of Yahoo but requires `ALPHA_VANTAGE_API_KEY`; without it the
secondary provider is skipped and Yahoo Chart remains the tertiary fallback.
`/api/v1/system/status` reports the configured chain and the last successful
provider by ticker.

### Frontend authentication

The frontend uses only `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` to get
the current session, then sends its access token as `Authorization: Bearer` on
API calls. The backend verifies the JWT against `SUPABASE_JWKS_URL` and uses
the `sub` claim for portfolio ownership. Never add service-role or Veyra API
keys to `VITE_` variables.

---

## 12. Database Domain

The database is designed around Veyra's portfolio-management workflow.

Core entities include, where implemented:

```text
User
 │
 └── Portfolio
       │
       ├── Holdings
       ├── Portfolio Snapshots
       ├── Portfolio Events
       │
       ├── Triggers
       │      └── Trigger Events
       │
       └── Evaluations
              │
              ├── Evaluation Assets
              └── Allocation Decisions
                       │
                       └── Rebalance Cycle
                              │
                              └── Orders
```

Feedback and historical evaluation information can be associated with subsequent control cycles.

---

## 13. Repository Structure

The repository follows a layered architecture.

```text
veyra/
│
├── backend/
│   ├── api/
│   ├── schemas/
│   ├── services/
│   ├── dependencies/
│   ├── middleware/
│   └── main.py
│
├── quant_engine/
│   ├── data/
│   ├── features/
│   ├── signals/
│   ├── factors/
│   ├── volatility/
│   ├── regimes/
│   ├── signal_control/
│   ├── reliability/
│   ├── risk/
│   ├── control/
│   ├── optimization/
│   └── evaluation/
│
├── database/
│   ├── models/
│   ├── repositories/
│   ├── migrations/
│   └── session.py
│
├── execution/
│   ├── paper/
│   ├── orders/
│   └── rebalance/
│
├── backtesting/
│
├── frontend/
│   └── src/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── quant_engine/
│
├── docs/
│   ├── architecture/
│   ├── formulas/
│   ├── api/
│   └── patent/
│
├── scripts/
│
└── config/
```

The exact repository contents may evolve as implementation progresses.

---

## 14. Technology Stack

### Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

### Quantitative Engine

- NumPy
- Pandas
- SciPy
- ARCH / GARCH tooling
- CVXPY where optimization is enabled

### Database / Infrastructure

- Supabase
- PostgreSQL
- SQLAlchemy
- Alembic

### Authentication

- Supabase Auth
- JWT

### Testing

- Pytest
- API/integration testing
- Frontend build/testing

---

## 15. Research and Validation

The quantitative research foundation includes historical equity-market analysis with:

- Technical feature generation
- GJR-GARCH volatility estimation
- Fama-French factor exposures
- Monthly universe selection
- Forward-return analysis
- Multifactor ranking
- Inverse-volatility sizing
- Stress filtering
- Portfolio diagnostics
- Backtesting

The research notebook serves as a quantitative research foundation. Production implementation is kept modular rather than copying notebook code directly into API routes.

Important research considerations include:

- Lookahead prevention
- Walk-forward validation
- Data-frequency consistency
- Survivorship bias
- Reproducibility
- Parameter stability

---

## 16. Performance Evaluation

Veyra's system evaluation is not limited to return maximization.

The architecture considers technical behavior such as:

- Allocation stability
- Maximum drawdown
- Portfolio turnover
- Signal stability
- Volatility response
- Regime robustness
- Risk behavior

Standard portfolio metrics may include:

- Sharpe ratio
- Calmar ratio
- Maximum drawdown
- Turnover

These metrics are used to evaluate system behavior and portfolio outcomes.

---

## 17. Development Principles

### Separation of concerns

The frontend should not contain quantitative formulas.

API routes should not implement quantitative calculations.

Repositories should not contain portfolio-control mathematics.

The optimizer should not know about PostgreSQL.

Execution should not decide whether the system should rebalance.

The backtester should not call live execution.

### Typed contracts

Data passed between modules should use explicit typed models wherever practical.

### No fake implementations

Avoid:

- random values
- placeholder outputs
- `pass`
- `TODO` in supposedly implemented functionality
- `NotImplementedError` for required paths
- hardcoded market results

### Lookahead safety

Production evaluation must distinguish information available at the evaluation timestamp from information observed later.

---

## 18. Current Development Scope

Veyra is being developed incrementally.

The major implementation stages are:

```text
Phase 1
Foundation
    ↓
Phase 2
Market Data + Features
    ↓
Phase 3
Volatility + Regime
    ↓
Phase 4
Signal Regulation + State-Coupled Control
    ↓
Phase 5
Reliability + Composite Risk
    ↓
Phase 6
Optimization + Allocation
    ↓
Rebalancing / Execution
    ↓
Feedback + Adaptive Threshold
    ↓
Production Hardening
```

Not every component is necessarily enabled in every development build.

---

## 19. Safety and Execution

The initial product architecture should separate:

```text
Decision
   ≠
Execution
```

An evaluation may generate a recommended target allocation without transmitting a live order.

Paper execution can be used for validation before broker integration.

Broker-connected execution should only be introduced after the decision, allocation, portfolio-state, and safety layers have been validated.

---

## 20. Disclaimer

Veyra is a technical portfolio-management research and software project.

Quantitative outputs, portfolio evaluations, target allocations, and risk states are model-generated outputs and may be wrong or incomplete.

The software should not be interpreted as a guarantee of investment performance or as a substitute for appropriate financial, legal, or regulatory review.

---

## 21. Project Vision

Veyra is designed around a simple principle:

> **Don't react to every market movement. Detect when the portfolio's state has changed enough to justify a different allocation.**

The long-term goal is a closed-loop portfolio-control system in which:

```text
Market State
     ↓
Portfolio State
     ↓
Risk + Reliability
     ↓
State-Coupled Control
     ↓
Allocation Decision
     ↓
Portfolio Outcome
     ↓
Feedback
     ↓
Adapted Future Control
```

This makes Veyra a **volatility-driven portfolio management and allocation-control system**, rather than a conventional stock-picking or trading application.
