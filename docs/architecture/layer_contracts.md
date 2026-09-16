# Layer Contracts

Veyra enforces strict architectural boundaries. Each layer communicates through explicit contracts.

## 1. Frontend → API

- **Input:** JSON HTTP request
- **Output:** JSON HTTP response with appropriate status codes (e.g., 201, 202, 404, 422)
- **Responsibility:** Request routing and basic validation.
- **Must Not Do:** Execute business rules, calculate quant signals, execute raw SQL.

## 2. API → Service

- **Input:** Primitive types (strings, UUIDs) and Pydantic Request schemas (e.g., `EvaluationRequest`).
- **Output:** Domain models (e.g., `EvaluationResult`, `Portfolio`).
- **Responsibility:** Orchestrate the application use cases.
- **Must Not Do:** Handle HTTP request/response objects directly, depend on FastAPI components.

## 3. Service → Domain

- **Input:** Raw data (from DB or API).
- **Output:** Validated Pydantic models.
- **Responsibility:** Ensure business rules (e.g., portfolio weights sum to 1).
- **Must Not Do:** Contain SQLAlchemy mappings, depend on database connections.

## 4. Service → Repository

- **Input:** Primitive types (strings, UUIDs, floats).
- **Output:** SQLAlchemy Models (e.g., `PortfolioModel`, `EvaluationModel`).
- **Responsibility:** Abstract persistence logic.
- **Must Not Do:** Contain business decisions (e.g., calculating portfolio weight or deciding to HOLD/REBALANCE).

## 5. Repository → Database

- **Input:** SQLAlchemy ORM commands.
- **Output:** Database rows.
- **Responsibility:** Data storage and retrieval.
- **Must Not Do:** Assume application-level validation is sufficient (must use DB constraints).

### Service → Quant Engine (Phase 2: Features)
- **Input:** Ticker and Date Range.
- **Output:** Validated, normalized `FeatureSnapshot` models.
- **Responsibility:** Fetch raw OHLCV, validate data integrity, compute technical features strictly without lookahead bias.
- **Must Not Do:** Implement portfolio rebalancing logic, determine volatility regimes, run GARCH, or persist data to PostgreSQL (persistence is deferred to later phases).

### Service → Quant Engine (Phase 3+: Allocations)
- **Input:** `Portfolio` domain model.
- **Output:** Target allocation or `EvaluationDecision`.
- **Responsibility:** Generate actionable trading decisions based on quantitative models.

### Quant Engine → Execution
- **Input:** Target allocation, approved rebalance proposal.
- **Output:** Trade orders (Buy/Sell/Hold).

### Execution → Feedback
- **Input:** Executed trades and slippage data.
- **Output:** Adaptive threshold adjustments for the GARCH model.
