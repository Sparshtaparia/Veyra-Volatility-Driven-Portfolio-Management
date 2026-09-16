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
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

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
    factor_states: Mapped[list["FactorStateModel"]] = relationship(
        "FactorStateModel", back_populates="portfolio", cascade="all, delete-orphan"
    )
    risk_states: Mapped[list["RiskStateModel"]] = relationship(
        "RiskStateModel", back_populates="portfolio", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("total_value >= 0", name="check_portfolio_total_value_non_negative"),
    )


class HoldingModel(Base):
    """
    Persistent state of a single holding within a portfolio.
    """

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    portfolio: Mapped["PortfolioModel"] = relationship("PortfolioModel", back_populates="holdings")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="check_holding_quantity_non_negative"),
        CheckConstraint("average_price >= 0", name="check_holding_average_price_non_negative"),
        CheckConstraint("current_price >= 0", name="check_holding_current_price_non_negative"),
        CheckConstraint("market_value >= 0", name="check_holding_market_value_non_negative"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="check_holding_weight_bounds"),
    )


class EvaluationModel(Base):
    """
    Persistent record of a portfolio evaluation cycle.
    evaluation_id is the primary correlation key across the system.
    """

    __tablename__ = "evaluations"

    evaluation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger: Mapped[EvaluationTrigger] = mapped_column(Enum(EvaluationTrigger), nullable=False)
    decision: Mapped[EvaluationDecision] = mapped_column(Enum(EvaluationDecision), nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    portfolio: Mapped["PortfolioModel"] = relationship(
        "PortfolioModel", back_populates="evaluations"
    )
    volatility_states: Mapped[list["VolatilityStateModel"]] = relationship(
        "VolatilityStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    regime_states: Mapped[list["RegimeStateModel"]] = relationship(
        "RegimeStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    factor_states: Mapped[list["FactorStateModel"]] = relationship(
        "FactorStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    fama_french_exposures: Mapped[list["FamaFrenchExposureModel"]] = relationship(
        "FamaFrenchExposureModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    reliability_states: Mapped[list["ReliabilityStateModel"]] = relationship(
        "ReliabilityStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    risk_states: Mapped[list["RiskStateModel"]] = relationship(
        "RiskStateModel", back_populates="evaluation", cascade="all, delete-orphan"
    )
    controlled_signals: Mapped[list["ControlledSignalModel"]] = relationship(
        "ControlledSignalModel", back_populates="evaluation", cascade="all, delete-orphan"
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

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


class FactorStateModel(Base):
    __tablename__ = "factor_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="CASCADE")
    )
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    normalization_method: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_factors: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    normalized_factors: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    factor_contributions: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    base_signal: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluation: Mapped["EvaluationModel"] = relationship(back_populates="factor_states")
    portfolio: Mapped["PortfolioModel"] = relationship(back_populates="factor_states")
    __table_args__ = (
        UniqueConstraint("evaluation_id", "ticker", name="uq_factor_state_evaluation_ticker"),
        Index("ix_factor_states_evaluation_id", "evaluation_id"),
        Index("ix_factor_states_portfolio_date", "portfolio_id", "as_of_date"),
    )


class FamaFrenchExposureModel(Base):
    __tablename__ = "fama_french_exposures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, nullable=False)
    market_beta: Mapped[float] = mapped_column(Float, nullable=False)
    smb_beta: Mapped[float] = mapped_column(Float, nullable=False)
    hml_beta: Mapped[float] = mapped_column(Float, nullable=False)
    rmw_beta: Mapped[float] = mapped_column(Float, nullable=False)
    cma_beta: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared: Mapped[float] = mapped_column(Float, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluation: Mapped["EvaluationModel"] = relationship(back_populates="fama_french_exposures")
    __table_args__ = (
        UniqueConstraint("evaluation_id", "ticker", name="uq_ff_exposure_evaluation_ticker"),
        Index("ix_ff_exposures_evaluation_id", "evaluation_id"),
    )


class ReliabilityStateModel(Base):
    __tablename__ = "reliability_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_reliability: Mapped[float] = mapped_column(Float, nullable=False)
    volatility_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    regime_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    recent_performance_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    reliability_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    effective_reliability: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluation: Mapped["EvaluationModel"] = relationship(back_populates="reliability_states")
    __table_args__ = (
        UniqueConstraint("evaluation_id", "ticker", name="uq_reliability_evaluation_ticker"),
        Index("ix_reliability_states_evaluation_id", "evaluation_id"),
    )


class RiskStateModel(Base):
    __tablename__ = "risk_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluations.evaluation_id", ondelete="CASCADE"),
        unique=True,
    )
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    volatility_risk: Mapped[float] = mapped_column(Float, nullable=False)
    drawdown_risk: Mapped[float] = mapped_column(Float, nullable=False)
    correlation_risk: Mapped[float] = mapped_column(Float, nullable=False)
    concentration_risk: Mapped[float] = mapped_column(Float, nullable=False)
    liquidity_risk: Mapped[float] = mapped_column(Float, nullable=False)
    composite_risk: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluation: Mapped["EvaluationModel"] = relationship(back_populates="risk_states")
    portfolio: Mapped["PortfolioModel"] = relationship(back_populates="risk_states")
    __table_args__ = (Index("ix_risk_states_portfolio_date", "portfolio_id", "as_of_date"),)


class ControlledSignalModel(Base):
    __tablename__ = "controlled_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_signal: Mapped[float] = mapped_column(Float, nullable=False)
    volatility_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    reliability_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    risk_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    controlled_signal: Mapped[float] = mapped_column(Float, nullable=False)
    risk_contribution: Mapped[float] = mapped_column(Float, nullable=False)
    explainability: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluation: Mapped["EvaluationModel"] = relationship(back_populates="controlled_signals")
    __table_args__ = (
        UniqueConstraint("evaluation_id", "ticker", name="uq_controlled_signal_evaluation_ticker"),
        Index("ix_controlled_signals_evaluation_id", "evaluation_id"),
    )


class PortfolioTargetModel(Base):
    __tablename__ = "portfolio_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="CASCADE")
    )
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(String, nullable=False)
    current_weight: Mapped[float] = mapped_column(Float, nullable=False)
    inverse_volatility_weight: Mapped[float] = mapped_column(Float, nullable=False)
    target_weight: Mapped[float] = mapped_column(Float, nullable=False)
    weight_change: Mapped[float] = mapped_column(Float, nullable=False)
    gross_exposure: Mapped[float] = mapped_column(Float, nullable=False)
    net_exposure: Mapped[float] = mapped_column(Float, nullable=False)
    cash_weight: Mapped[float] = mapped_column(Float, nullable=False)
    expected_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("evaluation_id", "ticker", name="uq_portfolio_target_evaluation_ticker"),
        CheckConstraint("current_weight >= 0 AND current_weight <= 1", name="ck_target_current"),
        CheckConstraint("target_weight >= 0 AND target_weight <= 1", name="ck_target_weight"),
        CheckConstraint("gross_exposure >= 0 AND gross_exposure <= 1", name="ck_target_gross"),
        CheckConstraint("net_exposure >= 0 AND net_exposure <= 1", name="ck_target_net"),
        CheckConstraint("cash_weight >= 0 AND cash_weight <= 1", name="ck_target_cash"),
        CheckConstraint("expected_volatility >= 0", name="ck_target_volatility"),
        Index("ix_portfolio_targets_portfolio_date", "portfolio_id", "as_of_date"),
    )


class RebalanceEventModel(Base):
    __tablename__ = "rebalance_events"

    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluations.evaluation_id", ondelete="CASCADE"),
        unique=True,
    )
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        CheckConstraint("portfolio_value >= 0", name="ck_rebalance_value"),
        CheckConstraint("turnover >= 0", name="ck_rebalance_turnover"),
        CheckConstraint("total_cost >= 0", name="ck_rebalance_cost"),
    )


class TradeModel(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("rebalance_events.event_id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    reference_price: Mapped[float] = mapped_column(Float, nullable=False)
    execution_price: Mapped[float] = mapped_column(Float, nullable=False)
    gross_notional: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_cost: Mapped[float] = mapped_column(Float, nullable=False)
    slippage_cost: Mapped[float] = mapped_column(Float, nullable=False)
    net_cash_change: Mapped[float] = mapped_column(Float, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trade_side"),
        CheckConstraint("quantity > 0", name="ck_trade_quantity"),
        CheckConstraint("reference_price > 0", name="ck_trade_reference_price"),
        CheckConstraint("execution_price > 0", name="ck_trade_execution_price"),
        CheckConstraint("gross_notional > 0", name="ck_trade_notional"),
        CheckConstraint("transaction_cost >= 0", name="ck_trade_transaction_cost"),
        CheckConstraint("slippage_cost >= 0", name="ck_trade_slippage_cost"),
        Index("ix_trades_event_id", "event_id"),
    )


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    evaluation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="SET NULL")
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)
    cash_value: Mapped[float] = mapped_column(Float, nullable=False)
    gross_exposure: Mapped[float] = mapped_column(Float, nullable=False)
    net_exposure: Mapped[float] = mapped_column(Float, nullable=False)
    holdings: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("portfolio_id", "snapshot_date", name="uq_portfolio_snapshot_date"),
        CheckConstraint("portfolio_value >= 0", name="ck_snapshot_value"),
        CheckConstraint("cash_value >= 0", name="ck_snapshot_cash"),
        CheckConstraint("gross_exposure >= 0 AND gross_exposure <= 1", name="ck_snapshot_gross"),
        CheckConstraint("net_exposure >= 0 AND net_exposure <= 1", name="ck_snapshot_net"),
        Index("ix_portfolio_snapshots_portfolio_date", "portfolio_id", "snapshot_date"),
    )


class FeedbackUpdateModel(Base):
    __tablename__ = "feedback_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evaluations.evaluation_id", ondelete="CASCADE")
    )
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    controlled_signal: Mapped[float] = mapped_column(Float, nullable=False)
    observed_outcome: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    updated_state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_feedback_updates_portfolio_date", "portfolio_id", "observation_date"),
    )


class BacktestModel(Base):
    __tablename__ = "backtests"

    backtest_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BacktestReturnModel(Base):
    __tablename__ = "backtest_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("backtests.backtest_id", ondelete="CASCADE")
    )
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    rebalance_date: Mapped[date] = mapped_column(Date, nullable=False)
    execution_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_realization_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_return: Mapped[float] = mapped_column(Float, nullable=False)
    net_return: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_return: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_cost: Mapped[float] = mapped_column(Float, nullable=False)
    __table_args__ = (
        UniqueConstraint("backtest_id", "return_realization_date", name="uq_backtest_return_date"),
        CheckConstraint("turnover >= 0", name="ck_backtest_return_turnover"),
        CheckConstraint("transaction_cost >= 0", name="ck_backtest_return_cost"),
        Index("ix_backtest_returns_backtest_date", "backtest_id", "return_realization_date"),
    )


class BacktestMetricModel(Base):
    __tablename__ = "backtest_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("backtests.backtest_id", ondelete="CASCADE"), unique=True
    )
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    cagr: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    sortino: Mapped[float] = mapped_column(Float, nullable=False)
    calmar: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, nullable=False)
    beta: Mapped[float] = mapped_column(Float, nullable=False)
    attribution: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    __table_args__ = (
        CheckConstraint("max_drawdown >= 0", name="ck_backtest_metric_drawdown"),
        CheckConstraint("volatility >= 0", name="ck_backtest_metric_volatility"),
        CheckConstraint("win_rate >= 0 AND win_rate <= 1", name="ck_backtest_metric_win_rate"),
        CheckConstraint("turnover >= 0", name="ck_backtest_metric_turnover"),
    )


class ScheduledRunModel(Base):
    """Operational ledger for idempotent scheduled pipeline claims."""

    __tablename__ = "scheduled_runs"

    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    portfolio_id: Mapped[str] = mapped_column(
        String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    evaluation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluations.evaluation_id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    stage_timings: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "run_type",
            "portfolio_id",
            "evaluation_date",
            name="uq_scheduled_run_type_portfolio_date",
        ),
        CheckConstraint(
            "run_type IN ('FULL_EVALUATION', 'VOLATILITY_REFRESH')",
            name="ck_scheduled_run_type",
        ),
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_scheduled_run_status",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_scheduled_run_duration",
        ),
        Index("ix_scheduled_runs_status", "status"),
        Index("ix_scheduled_runs_portfolio_date", "portfolio_id", "evaluation_date"),
    )
