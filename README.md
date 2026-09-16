# Veyra — Volatility-Driven Portfolio Management

Veyra is a backend system designed for volatility-driven portfolio management. It evaluates existing portfolios and determines whether to hold or rebalance based on changing market conditions and quantitative signals.

## Architecture
- **API**: FastAPI
- **Database**: Supabase PostgreSQL via SQLAlchemy 2.x and Alembic
- **Validation**: Pydantic v2
- **Testing**: pytest

## Setup

1. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

2. In Supabase, create a project and copy its transaction-pooler URI into
   `DATABASE_URL` (include `?sslmode=require`). Copy the project URL and anon
   key into both the root `.env` and `frontend/.env`; see each `.env.example`.
   The frontend uses Supabase Auth and sends its access token to this API.

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

## Phase Roadmap

- **Phase 1: Foundation** - API, database, domain models.
- **Phase 2: Market data + features** - OHLCV data and technical indicators.
- **Phase 3: GJR-GARCH + volatility regime** - Conditional volatility modeling.
- **Phase 4: Fama-French + alpha** - Rolling betas and multi-factor ranking.
- **Phase 5: Risk + reliability + control** - State-coupled signal regulation.
- **Phase 6: Optimization + rebalance** - Target allocation calculation.
- **Phase 7: Execution + feedback** - Paper trading and adaptive threshold updates.
