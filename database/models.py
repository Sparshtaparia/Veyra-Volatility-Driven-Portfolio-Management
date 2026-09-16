"""
database/models.py
==================
SQLAlchemy 2.x Declarative Models.

These models define the persistent storage schema.
They must NOT contain any quantitative logic or business decisions.

Constraints are enforced here at the DB level, complementing the
Pydantic validation in the domain layer.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHFitStatus,
    MarketRegime,
)


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
    volatility_states: Mapped[list["VolatilityStateModel"]] = relationship(
        "VolatilityStateModel", back_populates="portfolio", cascade="all, delete-orphan"
    )
    regime_states: Mapped[list["RegimeStateModel"]] = relationship(
        "RegimeStateModel", back_populates="portfolio", cascade="all, delete-orphan"
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
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger: Mapped[EvaluationTrigger] = mapped_column(Enum(EvaluationTrigger), nullable=False)
    decision: Mapped[EvaluationDecision] = mapped_column(Enum(EvaluationDecision), nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    portfolio: Mapped["PortfolioModel"] = relationship("PortfolioModel", back_populates="evaluations")
    volatility_states: Mapped[list["VolatilityStateModel"]] = relationship(
        "VolatilityStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    regime_states: Mapped[list["RegimeStateModel"]] = relationship(
        "RegimeStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )


class VolatilityStateModel(Base):
    """Persisted per-asset output from one correlated volatility evaluation."""

    __tablename__ = "volatility_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluations.evaluation_id", ondelete="CASCADE"),
        nullable=False,
    )
    portfolio_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    omega: Mapped[float | None] = mapped_column(Float, nullable=True)
    alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    gamma: Mapped[float | None] = mapped_column(Float, nullable=True)
    beta: Mapped[float | None] = mapped_column(Float, nullable=True)
    persistence: Mapped[float | None] = mapped_column(Float, nullable=True)

    conditional_variance: Mapped[float] = mapped_column(Float, nullable=False)
    conditional_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    realized_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    volatility_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    fit_status: Mapped[GARCHFitStatus] = mapped_column(
        Enum(GARCHFitStatus, native_enum=False, length=32), nullable=False
    )
    convergence_status: Mapped[GARCHConvergenceStatus] = mapped_column(
        Enum(GARCHConvergenceStatus, native_enum=False, length=32), nullable=False
    )
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    used_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    evaluation: Mapped["EvaluationModel"] = relationship(
        "EvaluationModel", back_populates="volatility_states"
    )
    portfolio: Mapped["PortfolioModel"] = relationship(
        "PortfolioModel", back_populates="volatility_states"
    )

    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            "ticker",
            "as_of_date",
            name="uq_volatility_state_evaluation_ticker_date",
        ),
        CheckConstraint("conditional_variance >= 0", name="ck_vol_state_variance"),
        CheckConstraint("conditional_volatility >= 0", name="ck_vol_state_conditional"),
        CheckConstraint("forecast_volatility >= 0", name="ck_vol_state_forecast"),
        CheckConstraint("realized_volatility >= 0", name="ck_vol_state_realized"),
        CheckConstraint("volatility_ratio >= 0", name="ck_vol_state_ratio"),
        CheckConstraint("observation_count >= 0", name="ck_vol_state_observations"),
        Index("ix_volatility_states_evaluation_id", "evaluation_id"),
        Index("ix_volatility_states_portfolio_date", "portfolio_id", "as_of_date"),
        Index("ix_volatility_states_ticker_date", "ticker", "as_of_date"),
    )


class RegimeStateModel(Base):
    """Persisted cross-sectional market regime from one evaluation."""

    __tablename__ = "regime_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluations.evaluation_id", ondelete="CASCADE"),
        nullable=False,
    )
    portfolio_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_asset_count: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_asset_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_fit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_count: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_asset_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False)

    aggregate_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    median_realized_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    median_volatility_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    ratio_iqr: Mapped[float] = mapped_column(Float, nullable=False)
    stress_score: Mapped[float] = mapped_column(Float, nullable=False)
    adaptive_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    distance_to_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[MarketRegime] = mapped_column(
        Enum(MarketRegime, native_enum=False, length=32), nullable=False
    )
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    evaluation: Mapped["EvaluationModel"] = relationship(
        "EvaluationModel", back_populates="regime_states"
    )
    portfolio: Mapped["PortfolioModel"] = relationship(
        "PortfolioModel", back_populates="regime_states"
    )

    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            "as_of_date",
            name="uq_regime_state_evaluation_date",
        ),
        CheckConstraint("total_asset_count > 0", name="ck_regime_total_assets"),
        CheckConstraint("eligible_asset_count >= 0", name="ck_regime_eligible_assets"),
        CheckConstraint("model_fit_count >= 0", name="ck_regime_fit_count"),
        CheckConstraint("fallback_count >= 0", name="ck_regime_fallback_count"),
        CheckConstraint("failed_asset_count >= 0", name="ck_regime_failed_count"),
        CheckConstraint("excluded_count >= 0", name="ck_regime_excluded_count"),
        CheckConstraint("aggregate_volatility >= 0", name="ck_regime_aggregate_vol"),
        CheckConstraint("median_realized_volatility >= 0", name="ck_regime_realized_vol"),
        CheckConstraint("median_volatility_ratio >= 0", name="ck_regime_median_ratio"),
        CheckConstraint("ratio_iqr >= 0", name="ck_regime_ratio_iqr"),
        CheckConstraint("stress_score >= 0", name="ck_regime_stress_score"),
        CheckConstraint("adaptive_threshold >= 0", name="ck_regime_threshold"),
        CheckConstraint(
            "coverage_ratio >= 0 AND coverage_ratio <= 1",
            name="ck_regime_coverage_ratio",
        ),
        Index("ix_regime_states_evaluation_id", "evaluation_id"),
        Index("ix_regime_states_portfolio_date", "portfolio_id", "as_of_date"),
    )
