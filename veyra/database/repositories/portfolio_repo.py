"""
database/repositories/portfolio_repo.py
=======================================
Persistence layer for Portfolios and Holdings.

Must NOT contain any quantitative logic or business decisions.
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from database.models import PortfolioModel, HoldingModel


class PortfolioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_portfolio(self, portfolio_id: str, name: str, currency: str) -> PortfolioModel:
        db_portfolio = PortfolioModel(id=portfolio_id, name=name, currency=currency)
        self.db.add(db_portfolio)
        self.db.commit()
        self.db.refresh(db_portfolio)
        return db_portfolio

    def get_portfolio(self, portfolio_id: str) -> Optional[PortfolioModel]:
        return self.db.execute(
            select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        ).scalar_one_or_none()

    def list_portfolios(self) -> List[PortfolioModel]:
        return list(self.db.execute(select(PortfolioModel)).scalars().all())

    def update_portfolio(self, portfolio: PortfolioModel) -> PortfolioModel:
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio
    
    def add_holding(self, portfolio_id: str, ticker: str, quantity: float, average_price: float, current_price: float, market_value: float, weight: float) -> HoldingModel:
        holding = HoldingModel(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            average_price=average_price,
            current_price=current_price,
            market_value=market_value,
            weight=weight
        )
        self.db.add(holding)
        self.db.commit()
        self.db.refresh(holding)
        return holding

    def get_holdings(self, portfolio_id: str) -> List[HoldingModel]:
        return list(self.db.execute(
            select(HoldingModel).where(HoldingModel.portfolio_id == portfolio_id)
        ).scalars().all())

    def update_holding(self, holding: HoldingModel) -> HoldingModel:
        self.db.commit()
        self.db.refresh(holding)
        return holding

    def remove_holding(self, holding_id: int) -> None:
        holding = self.db.execute(
            select(HoldingModel).where(HoldingModel.id == holding_id)
        ).scalar_one_or_none()
        if holding:
            self.db.delete(holding)
            self.db.commit()
