"""
backend/main.py
===============
FastAPI application factory and entrypoint.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import market_data, portfolios, volatility
from backend.exceptions import EvaluationNotFoundError, PortfolioNotFoundError, InvalidPortfolioError, InvalidEvaluationError
from backend.middleware.logging import LoggingMiddleware
from config.settings import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Routers
app.include_router(portfolios.router, prefix=settings.api_prefix)
app.include_router(market_data.router, prefix=settings.api_prefix)
app.include_router(volatility.router, prefix=settings.api_prefix)

# Healthcheck
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

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
