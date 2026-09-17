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
        if user_id is not None and portfolio.user_id is not None:
            if portfolio.user_id != user_id:
                # Surface as 404 to avoid leaking existence to unauthorized users.
                raise PortfolioNotFoundError(portfolio.id)

    def update_portfolio(
        self,
        portfolio_id: str,
        name: str | None = None,
        currency: str | None = None,
        max_weight_constraint: float | None = None,
        *,
        user_id: str | None = None,
    ) -> PortfolioModel:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)
        self._assert_ownership(portfolio, user_id)

        if name is not None:
            portfolio.name = name.strip()
        if currency is not None:
            portfolio.currency = currency.strip().upper()
        if max_weight_constraint is not None:
            if not (0.05 <= max_weight_constraint <= 1.0):
                raise ValueError("max_weight_constraint must be between 0.05 and 1.0")
            portfolio.max_weight_constraint = max_weight_constraint

        return self.repo.update_portfolio(portfolio)

    def delete_portfolio(self, portfolio_id: str, user_id: str | None = None) -> None:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)
        self._assert_ownership(portfolio, user_id)
        self.repo.delete_portfolio(portfolio_id)

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

    def update_holding(
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

        holdings = self.repo.get_holdings(portfolio_id)
        holding = next((h for h in holdings if h.ticker == ticker), None)
        if not holding:
            raise ValueError(f"Holding {ticker} not found in portfolio")

        holding.quantity = quantity
        holding.average_price = average_price
        holding.current_price = current_price
        holding.market_value = quantity * current_price
        self.repo.update_holding(holding)
        
        self._recalculate_weights(portfolio_id)
        return holding

    def delete_holding(self, portfolio_id: str, ticker: str, user_id: str | None = None) -> None:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        self._assert_ownership(portfolio, user_id)

        holdings = self.repo.get_holdings(portfolio_id)
        holding = next((h for h in holdings if h.ticker == ticker), None)
        if not holding:
            raise ValueError(f"Holding {ticker} not found in portfolio")

        self.repo.remove_holding(holding.id)
        self._recalculate_weights(portfolio_id)

    def _recalculate_weights(self, portfolio_id: str) -> None:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        holdings = self.repo.get_holdings(portfolio_id)
        total_value = sum(h.market_value for h in holdings)
        
        portfolio.total_value = total_value
        for holding in holdings:
            holding.weight = holding.market_value / total_value if total_value > 0 else 0.0
            self.repo.update_holding(holding)

        self.repo.update_portfolio(portfolio)

    def sync_prices(self, portfolio_id: str, as_of_date: date, provider: "MarketDataProvider") -> None:
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            return

        holdings = self.repo.get_holdings(portfolio_id)
        if not holdings:
            return
            
        from datetime import timedelta
        
        for holding in holdings:
            bars = provider.get_history(holding.ticker, as_of_date - timedelta(days=7), as_of_date)
            valid = [b for b in bars if b.timestamp <= as_of_date]
            if valid:
                holding.current_price = valid[-1].close
                holding.market_value = holding.quantity * holding.current_price
                
        self.repo.update_portfolio(portfolio) # Flush
        self._recalculate_weights(portfolio_id)
    def to_domain(self, portfolio_id: str, as_of_date: date, user_id: str | None = None) -> Portfolio:
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
