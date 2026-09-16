"""Application orchestration for persisted Phase 3 volatility evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.exceptions import (
    EvaluationNotFoundError,
    InvalidEvaluationError,
    MarketDataUnavailableError,
    VolatilityEvaluationNotFoundError,
    VolatilityPersistenceError,
)
from backend.services.portfolio_service import PortfolioService
from database.models import EvaluationModel, RegimeStateModel, VolatilityStateModel
from database.repositories.evaluation_repo import EvaluationRepository
from database.repositories.regime_repo import RegimeRepository
from database.repositories.volatility_repo import VolatilityRepository
from quant_engine.data.provider import MarketDataProvider
from quant_engine.data.returns import calculate_log_returns
from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger
from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import StressObservation
from quant_engine.regimes.service import RegimeService
from quant_engine.volatility.models import GARCHFitStatus, MarketRegime
from quant_engine.volatility.service import VolatilityService


@dataclass(frozen=True)
class AssetVolatilityDTO:
    ticker: str
    conditional_volatility: float
    forecast_volatility: float
    realized_volatility: float
    volatility_ratio: float
    fit_status: GARCHFitStatus
    used_fallback: bool


@dataclass(frozen=True)
class MarketRegimeDTO:
    as_of_date: date
    stress_score: float
    adaptive_threshold: float
    regime: MarketRegime
    eligible_asset_count: int
    coverage_ratio: float
    distance_to_threshold: float


@dataclass(frozen=True)
class VolatilityEvaluationDTO:
    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    market_regime: MarketRegimeDTO
    asset_volatility: list[AssetVolatilityDTO]


class VolatilityEvaluationService:
    """Coordinate data retrieval, quant services, and atomic Phase 3 persistence."""

    def __init__(
        self,
        db: Session,
        market_data_provider: MarketDataProvider,
        *,
        volatility_service: VolatilityService | None = None,
        regime_service: RegimeService | None = None,
        history_lookback_days: int = 550,
    ) -> None:
        self.db = db
        self.market_data_provider = market_data_provider
        self.volatility_service = volatility_service or VolatilityService()
        self.regime_service = regime_service or RegimeService()
        self.history_lookback_days = history_lookback_days
        self.portfolio_service = PortfolioService(db)
        self.evaluation_repo = EvaluationRepository(db)
        self.volatility_repo = VolatilityRepository(db)
        self.regime_repo = RegimeRepository(db)

    def evaluate(
        self,
        portfolio_id: str,
        as_of_date: date,
        *,
        evaluation_id: UUID | None = None,
    ) -> VolatilityEvaluationDTO:
        self.portfolio_service.get_portfolio(portfolio_id)
        holdings = self.portfolio_service.repo.get_holdings(portfolio_id)
        if not holdings:
            requirements = self.volatility_service.aggregator.coverage_requirements
            raise InsufficientCoverageError(
                eligible_asset_count=0,
                total_asset_count=0,
                minimum_asset_count=requirements.minimum_asset_count,
                minimum_coverage_ratio=requirements.minimum_coverage_ratio,
            )

        evaluation = self._resolve_evaluation(portfolio_id, as_of_date, evaluation_id)
        resolved_evaluation_id = evaluation.evaluation_id
        existing = self.regime_repo.get_by_evaluation(resolved_evaluation_id)
        if existing is not None:
            return self._load_result(resolved_evaluation_id)

        try:
            returns_by_ticker = self._load_returns(
                {holding.ticker for holding in holdings}, as_of_date
            )
            volatility_result = self.volatility_service.evaluate(
                returns_by_ticker,
                as_of_date=as_of_date,
            )
            historical_rows = self.regime_repo.get_history_for_portfolio(
                portfolio_id,
                through_date=as_of_date,
            )
            history = [
                StressObservation(
                    timestamp=row.as_of_date,
                    stress_score=row.stress_score,
                    eligible_asset_count=row.eligible_asset_count,
                    coverage_ratio=row.coverage_ratio,
                )
                for row in historical_rows
            ]
            state = self.regime_service.evaluate(
                volatility_result.market_stress_snapshot,
                history,
            )
        except Exception as exc:
            self._mark_failed(resolved_evaluation_id, exc)
            raise

        try:
            self.volatility_repo.create_many(
                resolved_evaluation_id,
                portfolio_id,
                volatility_result.estimates,
            )
            self.regime_repo.create(
                resolved_evaluation_id,
                portfolio_id,
                state,
                volatility_result.market_stress_snapshot,
            )
            evaluation.status = EvaluationStatus.COMPLETED
            evaluation.completed_at = datetime.utcnow()
            evaluation.error_message = None
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if self.regime_repo.get_by_evaluation(resolved_evaluation_id) is not None:
                return self._load_result(resolved_evaluation_id)
            self._mark_failed(resolved_evaluation_id, exc)
            raise VolatilityPersistenceError("Could not persist volatility evaluation") from exc
        except Exception as exc:
            self.db.rollback()
            self._mark_failed(resolved_evaluation_id, exc)
            raise VolatilityPersistenceError("Could not persist volatility evaluation") from exc

        return self._load_result(resolved_evaluation_id)

    def get_evaluation(self, evaluation_id: UUID | str) -> VolatilityEvaluationDTO:
        return self._load_result(self._parse_evaluation_id(evaluation_id))

    def get_regime(self, evaluation_id: UUID | str) -> MarketRegimeDTO:
        evaluation_uuid = self._parse_evaluation_id(evaluation_id)
        record = self.regime_repo.get_by_evaluation(evaluation_uuid)
        if record is None:
            raise VolatilityEvaluationNotFoundError(str(evaluation_id))
        return self._regime_dto(record)

    def get_latest_regime(self, portfolio_id: str) -> MarketRegimeDTO:
        self.portfolio_service.get_portfolio(portfolio_id)
        record = self.regime_repo.get_latest_for_portfolio(portfolio_id)
        if record is None:
            raise VolatilityEvaluationNotFoundError(portfolio_id)
        return self._regime_dto(record)

    def _resolve_evaluation(
        self,
        portfolio_id: str,
        as_of_date: date,
        evaluation_id: UUID | None,
    ) -> EvaluationModel:
        resolved_id = evaluation_id or uuid4()
        existing = self.evaluation_repo.get_evaluation(resolved_id)
        if existing is not None:
            if existing.portfolio_id != portfolio_id:
                raise EvaluationNotFoundError(str(resolved_id))
            if existing.evaluation_date != as_of_date:
                raise InvalidEvaluationError(
                    "evaluation_id is already associated with a different date"
                )
            return existing
        return self.evaluation_repo.create_evaluation(
            evaluation_id=resolved_id,
            portfolio_id=portfolio_id,
            evaluation_date=as_of_date,
            trigger=EvaluationTrigger.MANUAL,
            decision=EvaluationDecision.HOLD,
            status=EvaluationStatus.PENDING,
        )

    def _load_returns(
        self,
        tickers: set[str],
        as_of_date: date,
    ) -> dict[str, pd.Series]:
        start_date = as_of_date - timedelta(days=self.history_lookback_days)
        end_date = as_of_date + timedelta(days=1)
        returns_by_ticker = {}
        for ticker in sorted(tickers):
            try:
                bars = self.market_data_provider.get_history(ticker, start_date, end_date)
            except Exception as exc:
                raise MarketDataUnavailableError(
                    "The configured market-data provider is unavailable"
                ) from exc
            returns_by_ticker[ticker] = calculate_log_returns(bars)
        return returns_by_ticker

    def _load_result(self, evaluation_id: UUID) -> VolatilityEvaluationDTO:
        evaluation = self.evaluation_repo.get_evaluation(evaluation_id)
        regime = self.regime_repo.get_by_evaluation(evaluation_id)
        assets = self.volatility_repo.get_by_evaluation(evaluation_id)
        if evaluation is None or regime is None:
            raise VolatilityEvaluationNotFoundError(str(evaluation_id))
        return VolatilityEvaluationDTO(
            evaluation_id=evaluation_id,
            portfolio_id=evaluation.portfolio_id,
            as_of_date=regime.as_of_date,
            market_regime=self._regime_dto(regime),
            asset_volatility=[self._asset_dto(asset) for asset in assets],
        )

    @staticmethod
    def _asset_dto(record: VolatilityStateModel) -> AssetVolatilityDTO:
        return AssetVolatilityDTO(
            ticker=record.ticker,
            conditional_volatility=record.conditional_volatility,
            forecast_volatility=record.forecast_volatility,
            realized_volatility=record.realized_volatility,
            volatility_ratio=record.volatility_ratio,
            fit_status=record.fit_status,
            used_fallback=record.used_fallback,
        )

    @staticmethod
    def _regime_dto(record: RegimeStateModel) -> MarketRegimeDTO:
        return MarketRegimeDTO(
            as_of_date=record.as_of_date,
            stress_score=record.stress_score,
            adaptive_threshold=record.adaptive_threshold,
            regime=record.regime,
            eligible_asset_count=record.eligible_asset_count,
            coverage_ratio=record.coverage_ratio,
            distance_to_threshold=record.distance_to_threshold,
        )

    @staticmethod
    def _parse_evaluation_id(evaluation_id: UUID | str) -> UUID:
        if isinstance(evaluation_id, UUID):
            return evaluation_id
        try:
            return UUID(hex=evaluation_id)
        except ValueError as exc:
            raise VolatilityEvaluationNotFoundError(evaluation_id) from exc

    def _mark_failed(self, evaluation_id: UUID, error: Exception) -> None:
        self.db.rollback()
        evaluation = self.evaluation_repo.get_evaluation(evaluation_id)
        if evaluation is None:
            return
        evaluation.status = EvaluationStatus.FAILED
        evaluation.completed_at = datetime.utcnow()
        evaluation.error_message = f"{type(error).__name__}: {error}"
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
