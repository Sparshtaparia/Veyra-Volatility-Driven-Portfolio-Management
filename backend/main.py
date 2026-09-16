"""
backend/main.py
===============
FastAPI application factory and entrypoint.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.api import market_data, portfolio_control, portfolios, signals, system, volatility, rebalance
from backend.dependencies.db import get_db
from backend.exceptions import (
    EvaluationNotFoundError,
    InvalidEvaluationError,
    InvalidPortfolioError,
    PortfolioNotFoundError,
)
from backend.middleware.logging import LoggingMiddleware
from backend.middleware.security import ApiSecurityMiddleware
from backend.operations.health import database_readiness
from backend.operations.logging import configure_logging
from backend.operations.scheduler import scheduler_service
from config.settings import get_settings

settings = get_settings()

configure_logging(settings.log_level, structured=settings.structured_json_logs)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler_service.start()
    try:
        yield
    finally:
        scheduler_service.stop()


app = FastAPI(
    title="Veyra API",
    description="Volatility-Driven Portfolio Management",
    version="0.2.0",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    ApiSecurityMiddleware,
    api_prefix=settings.api_prefix,
    api_key=settings.api_key.get_secret_value() if settings.api_key else None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# NOTE: Route-level JWT authentication is enforced via `require_auth` dependency
# in each protected API router. Health endpoints remain public.

# Routers
app.include_router(portfolios.router, prefix=settings.api_prefix)
app.include_router(market_data.router, prefix=settings.api_prefix)
app.include_router(volatility.router, prefix=settings.api_prefix)
app.include_router(signals.router, prefix=settings.api_prefix)
app.include_router(portfolio_control.router, prefix=settings.api_prefix)
app.include_router(system.router, prefix=settings.api_prefix)
app.include_router(rebalance.router, prefix=settings.api_prefix)


# Healthcheck
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "live"}


@app.get("/health/live", tags=["health"])
def liveness_check():
    return {"status": "live"}


@app.get("/health/ready", tags=["health"])
def readiness_check(db: Session = Depends(get_db)):
    try:
        state = database_readiness(db)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )
    if state["schema_status"] != "current":
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", **state},
        )
    return {"status": "ready", **state}


# Exception Handlers
@app.exception_handler(PortfolioNotFoundError)
async def portfolio_not_found_handler(request: Request, exc: PortfolioNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(EvaluationNotFoundError)
async def evaluation_not_found_handler(request: Request, exc: EvaluationNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidPortfolioError)
async def invalid_portfolio_handler(request: Request, exc: InvalidPortfolioError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidEvaluationError)
async def invalid_evaluation_handler(request: Request, exc: InvalidEvaluationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )
