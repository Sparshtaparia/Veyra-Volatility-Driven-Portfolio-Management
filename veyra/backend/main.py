"""
backend/main.py
===============
FastAPI application factory and entrypoint.
"""

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api import market_data, portfolio_control, portfolios, signals, volatility
from backend.dependencies.db import get_db
from backend.exceptions import (
    EvaluationNotFoundError,
    InvalidEvaluationError,
    InvalidPortfolioError,
    PortfolioNotFoundError,
)
from backend.middleware.logging import LoggingMiddleware
from config.settings import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Veyra API",
    description="Volatility-Driven Portfolio Management",
    version="0.1.0",
)

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(portfolios.router, prefix=settings.api_prefix)
app.include_router(market_data.router, prefix=settings.api_prefix)
app.include_router(volatility.router, prefix=settings.api_prefix)
app.include_router(signals.router, prefix=settings.api_prefix)
app.include_router(portfolio_control.router, prefix=settings.api_prefix)


# Healthcheck
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


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
