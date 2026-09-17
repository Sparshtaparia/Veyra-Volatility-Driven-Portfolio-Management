"""CSV/XLSX/manual portfolio ingestion using existing portfolio services."""

from datetime import date, timedelta
from io import BytesIO

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from backend.services.portfolio_service import PortfolioService
from quant_engine.data.provider import MarketDataProvider


class UploadedHolding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    quantity: float = Field(gt=0.0)
    average_price: float = Field(gt=0.0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("ticker must not be empty")
        return value


class PortfolioUploadService:
    REQUIRED_COLUMNS = {"ticker", "quantity", "average_price"}

    def __init__(self, db: Session, market_data_provider: MarketDataProvider) -> None:
        self.portfolios = PortfolioService(db)
        self.market_data_provider = market_data_provider

    def parse(self, content: bytes, filename: str) -> list[UploadedHolding]:
        suffix = filename.lower().rsplit(".", maxsplit=1)[-1]
        if suffix == "csv":
            frame = pd.read_csv(BytesIO(content))
        elif suffix == "xlsx":
            frame = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("portfolio file must be CSV or XLSX")
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        missing = self.REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"portfolio file is missing columns: {', '.join(sorted(missing))}")
        return [UploadedHolding.model_validate(row) for row in frame.to_dict(orient="records")]

    def create_portfolio(
        self,
        name: str,
        currency: str,
        holdings: list[UploadedHolding],
        as_of_date: date,
        user_id: str,
    ):
        if not holdings:
            raise ValueError("portfolio upload must contain at least one holding")
        tickers = [holding.ticker for holding in holdings]
        if len(tickers) != len(set(tickers)):
            raise ValueError("portfolio upload contains duplicate tickers")
        prices: dict[str, float] = {}
        for holding in holdings:
            bars = self.market_data_provider.get_history(
                holding.ticker, as_of_date - timedelta(days=14), as_of_date + timedelta(days=1)
            )
            eligible = [bar for bar in bars if bar.timestamp <= as_of_date]
            if not eligible:
                raise ValueError(f"No current price available for {holding.ticker}")
            prices[holding.ticker] = eligible[-1].close
        portfolio = self.portfolios.create_portfolio(name, currency, user_id=user_id)
        for holding in holdings:
            self.portfolios.add_holding(
                portfolio.id,
                holding.ticker,
                holding.quantity,
                holding.average_price,
                prices[holding.ticker],
                user_id=user_id,
            )
        return self.portfolios.get_portfolio(portfolio.id, user_id=user_id)
