"""
backend/services/portfolio_service.py
=====================================
Business logic for Portfolios.

Authorization rule: a user may only access/modify portfolios where
portfolio.user_id == their own Supabase user_id.  ADMIN users bypass
this check (handled at the API layer via require_admin).
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

    def create_portfolio(
        self, name: str, currency: str, user_id: str | None = None
    ) -> PortfolioModel:
        portfolio_id = f"port-{uuid.uuid4().hex[:8]}"
        return self.repo.create_portfolio(
            portfolio_id=portfolio_id, name=name, currency=currency, user_id=user_id
        )

    def _assert_ownership(self, portfolio: PortfolioModel, user_id: str | None) -> None:
        """
        Raise PortfolioNotFoundError if the portfolio does not belong to the
        requesting user.  When user_id is None (e.g. internal/admin calls),
        ownership is not enforced.
        """
        if user_id is not None and portfolio.user_id != user_id:
            # Surface as 404 to avoid leaking existence to unauthorized users.
            raise PortfolioNotFoundError(portfolio.id)

    def add_holding(
        self,
        portfolio_id: str,
        ticker: str,
        quantity: float,
        average_price: float,
        current_price: float,
        user_id: str | None = None,
    ) -> HoldingModel:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        self._assert_ownership(portfolio, user_id)

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

    def to_domain(
        self, portfolio_id: str, as_of_date: date, user_id: str | None = None
    ) -> Portfolio:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        self._assert_ownership(portfolio, user_id)

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

    def get_portfolio(self, portfolio_id: str, user_id: str | None = None) -> PortfolioModel:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)
        self._assert_ownership(portfolio, user_id)
        return portfolio

    def list_portfolios_for_user(self, user_id: str) -> list[PortfolioModel]:
        return self.repo.list_portfolios_by_user(user_id)
