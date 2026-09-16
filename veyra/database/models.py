"""
database/models.py
==================
SQLAlchemy 2.x Declarative Models.

These models define the persistent storage schema.
They must NOT contain any quantitative logic or business decisions.

Constraints are enforced here at the DB level, complementing the
Pydantic validation in the domain layer.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger


class Base(DeclarativeBase):
    pass


class PortfolioModel(Base):
    """
    Persistent state of a portfolio.
    """
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    holdings: Mapped[list["HoldingModel"]] = relationship(
        "HoldingModel", back_populates="portfolio", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["EvaluationModel"]] = relationship(
        "EvaluationModel", back_populates="portfolio", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint('total_value >= 0', name='check_portfolio_total_value_non_negative'),
    )


class HoldingModel(Base):
    """
    Persistent state of a single holding within a portfolio.
    """
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    portfolio: Mapped["PortfolioModel"] = relationship("PortfolioModel", back_populates="holdings")

    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check_holding_quantity_non_negative'),
        CheckConstraint('average_price >= 0', name='check_holding_average_price_non_negative'),
        CheckConstraint('current_price >= 0', name='check_holding_current_price_non_negative'),
        CheckConstraint('market_value >= 0', name='check_holding_market_value_non_negative'),
        CheckConstraint('weight >= 0 AND weight <= 1', name='check_holding_weight_bounds'),
    )


class EvaluationModel(Base):
    """
    Persistent record of a portfolio evaluation cycle.
    evaluation_id is the primary correlation key across the system.
    """
    __tablename__ = "evaluations"

    evaluation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    evaluation_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    trigger: Mapped[EvaluationTrigger] = mapped_column(Enum(EvaluationTrigger), nullable=False)
    decision: Mapped[EvaluationDecision] = mapped_column(Enum(EvaluationDecision), nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    portfolio: Mapped["PortfolioModel"] = relationship("PortfolioModel", back_populates="evaluations")
