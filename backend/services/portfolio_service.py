"""
backend/services/portfolio_service.py
=====================================
Business logic for Portfolios.
"""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from backend.exceptions import InvalidPortfolioError, PortfolioNotFoundError
from database.models import HoldingModel, PortfolioModel
from database.repositories.portfolio_repo import PortfolioRepository
from quant_engine.domain import Portfolio, PortfolioHolding


class PortfolioService:
    def __init__(self, db: Session):
        self.repo = PortfolioRepository(db)

    def create_portfolio(self, name: str, currency: str) -> PortfolioModel:
        portfolio_id = f"port-{uuid.uuid4().hex[:8]}"
        return self.repo.create_portfolio(portfolio_id=portfolio_id, name=name, currency=currency)

    def add_holding(
        self,
        portfolio_id: str,
        ticker: str,
        quantity: float,
        average_price: float,
        current_price: float,
    ) -> HoldingModel:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        if quantity < 0 or average_price < 0 or current_price < 0:
            raise InvalidPortfolioError("Quantity and prices must be non-negative.")

        market_value = quantity * current_price

        # Add the holding initially with weight 0
        holding = self.repo.add_holding(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            average_price=average_price,
            current_price=current_price,
            market_value=market_value,
            weight=0.0,
        )

        self._recalculate_weights(portfolio_id)
        return holding

    def _recalculate_weights(self, portfolio_id: str) -> None:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            return

        holdings = self.repo.get_holdings(portfolio_id)

        # Calculate new total value
        total_value = sum(h.market_value for h in holdings)
        portfolio.total_value = total_value
        self.repo.update_portfolio(portfolio)

        # Update weights
        for h in holdings:
            if total_value > 0:
                h.weight = h.market_value / total_value
            else:
                h.weight = 0.0
            self.repo.update_holding(h)

    def to_domain(self, portfolio_id: str, as_of_date: date) -> Portfolio:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        holdings = self.repo.get_holdings(portfolio_id)
        domain_holdings = [
            PortfolioHolding(
                ticker=h.ticker, weight=h.weight, quantity=h.quantity, market_value=h.market_value
            )
            for h in holdings
        ]

        return Portfolio(
            portfolio_id=portfolio.id,
            holdings=domain_holdings,
            total_value=portfolio.total_value,
            as_of_date=as_of_date,
        )

    def get_portfolio(self, portfolio_id: str) -> PortfolioModel:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)
        return portfolio
