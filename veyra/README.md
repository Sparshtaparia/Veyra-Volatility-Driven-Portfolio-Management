# Veyra — Volatility-Driven Portfolio Management

Veyra is a backend system designed for volatility-driven portfolio management. It evaluates existing portfolios and determines whether to hold or rebalance based on changing market conditions and quantitative signals.

## Architecture
- **API**: FastAPI
- **Quant terminal**: React + TypeScript + Tailwind + Plotly
- **Database**: PostgreSQL 15 via SQLAlchemy 2.x and Alembic
- **Validation**: Pydantic v2
- **Testing**: pytest

## Setup

1. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

2. Start the database:
   ```bash
   docker compose up -d
   ```

3. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the server:
   ```bash
   uvicorn backend.main:app --reload
   ```

6. Start the quant terminal:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Or start PostgreSQL, the migrated API, and the production frontend together:

```bash
docker compose up --build
```

## Testing

Run the test suite (requires an active database or SQLite fallback):
```bash
pytest tests/ -v
```

## API Examples

### Create Portfolio
```bash
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "Content-Type: application/json" \
  -d '{"name": "My Portfolio", "currency": "INR"}'
```

### Add Holding
```bash
curl -X POST http://localhost:8000/api/v1/portfolios/port-1234abcd/holdings \
  -H "Content-Type: application/json" \
  -d '{"ticker": "TCS", "quantity": 20, "average_price": 3500, "current_price": 3600}'
```

### Get Market Data & Features
```bash
curl -X GET "http://localhost:8000/api/v1/portfolios/port-1234abcd/features?ticker=TCS&start_date=2024-01-01&end_date=2024-06-01" \
  -H "Accept: application/json"
```

### Evaluate Portfolio
```bash
curl -X POST http://localhost:8000/api/v1/portfolios/port-1234abcd/evaluate \
  -H "Content-Type: application/json" \
  -d '{"evaluation_date": "2026-09-16", "trigger": "MANUAL"}'
```

### Evaluate and Retrieve Volatility Regime

```bash
curl -X POST http://localhost:8000/api/v1/portfolios/port-1234abcd/volatility/evaluate \
  -H "Content-Type: application/json" \
  -d '{"as_of_date": "2026-09-16"}'

curl http://localhost:8000/api/v1/evaluations/EVALUATION_UUID/volatility
curl http://localhost:8000/api/v1/evaluations/EVALUATION_UUID/regime
curl http://localhost:8000/api/v1/portfolios/port-1234abcd/regime/latest
```

Phase 3 state is stored in PostgreSQL through SQLAlchemy. The volatility and
regime rows share the existing evaluation ID, and reusing a completed
evaluation ID returns the persisted result.

### Evaluate Controlled Signals

Configure `FAMA_FRENCH_DATA_PATH` with a decimal-return five-factor CSV, then:

```bash
curl -X POST http://localhost:8000/api/v1/portfolios/port-1234abcd/signals/evaluate \
  -H "Content-Type: application/json" \
  -d '{"as_of_date": "2026-09-16"}'

curl http://localhost:8000/api/v1/evaluations/EVALUATION_UUID/signals
curl http://localhost:8000/api/v1/evaluations/EVALUATION_UUID/risk
curl http://localhost:8000/api/v1/evaluations/EVALUATION_UUID/explainability
```

## Phase 5 portfolio control

Phase 5 completes the core loop with CSV/XLSX/manual ingestion, a
regime-and-risk exposure controller, inverse-volatility convex optimization,
paper rebalancing, deterministic state feedback, chronological walk-forward
backtesting, seven architecture ablations, and performance attribution.

See [the Phase 5 architecture and deployment guide](docs/phase5.md).

## Phase Roadmap

- **Phase 1: Foundation** - API, database, domain models.
- **Phase 2: Market data + features** - OHLCV data and technical indicators.
- **Phase 3: GJR-GARCH + volatility regime** - Conditional volatility modeling.
- **Phase 4: Fama-French + alpha** - Rolling betas and multi-factor ranking.
- **Phase 5: Final core** - Optimization, paper rebalance, feedback, backtesting,
  ablations, attribution, and the quant terminal.

Live broker execution and trade authorization remain intentionally out of scope.
