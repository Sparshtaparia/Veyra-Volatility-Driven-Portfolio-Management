"""Persistence boundary for Phase 4 intelligence outputs."""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    ControlledSignalModel,
    EvaluationModel,
    FactorStateModel,
    FamaFrenchExposureModel,
    ReliabilityStateModel,
    RiskStateModel,
)
from quant_engine.factors.models import BaseSignal, FactorSnapshot, FamaFrenchExposure
from quant_engine.reliability.models import ReliabilityState
from quant_engine.risk.models import RiskState
from quant_engine.signals.models import ControlledSignal, ExplainabilityPayload


class IntelligenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_bundle(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        *,
        factors: Sequence[FactorSnapshot],
        base_signals: Sequence[BaseSignal],
        exposures: Sequence[FamaFrenchExposure],
        reliabilities: Sequence[ReliabilityState],
        risk: RiskState,
        controlled_signals: Sequence[ControlledSignal],
        explanations: Sequence[ExplainabilityPayload],
        risk_contributions: dict[str, float],
    ) -> None:
        bases = {item.ticker: item for item in base_signals}
        explanation_by_ticker = {item.ticker: item for item in explanations}
        self.db.add_all(
            [
                FactorStateModel(
                    evaluation_id=evaluation_id,
                    portfolio_id=portfolio_id,
                    ticker=item.ticker,
                    as_of_date=item.as_of_date,
                    normalization_method=item.normalization_method.value,
                    raw_factors=item.raw_factors,
                    normalized_factors=item.normalized_factors,
                    factor_contributions=bases[item.ticker].contributions,
                    base_signal=bases[item.ticker].base_signal,
                )
                for item in factors
            ]
        )
        self.db.add_all(
            [
                FamaFrenchExposureModel(evaluation_id=evaluation_id, **item.model_dump())
                for item in exposures
            ]
        )
        self.db.add_all(
            [
                ReliabilityStateModel(evaluation_id=evaluation_id, **item.model_dump())
                for item in reliabilities
            ]
        )
        self.db.add(
            RiskStateModel(
                evaluation_id=evaluation_id, portfolio_id=portfolio_id, **risk.model_dump()
            )
        )
        self.db.add_all(
            [
                ControlledSignalModel(
                    evaluation_id=evaluation_id,
                    **item.model_dump(),
                    risk_contribution=risk_contributions[item.ticker],
                    explainability=explanation_by_ticker[item.ticker].model_dump(mode="json"),
                )
                for item in controlled_signals
            ]
        )
        self.db.flush()

    def has_evaluation(self, evaluation_id: UUID) -> bool:
        return self.get_risk(evaluation_id) is not None

    def get_factors(self, evaluation_id: UUID) -> list[FactorStateModel]:
        return list(
            self.db.scalars(
                select(FactorStateModel)
                .where(FactorStateModel.evaluation_id == evaluation_id)
                .order_by(FactorStateModel.ticker)
            ).all()
        )

    def get_exposures(self, evaluation_id: UUID) -> list[FamaFrenchExposureModel]:
        return list(
            self.db.scalars(
                select(FamaFrenchExposureModel)
                .where(FamaFrenchExposureModel.evaluation_id == evaluation_id)
                .order_by(FamaFrenchExposureModel.ticker)
            ).all()
        )

    def get_reliabilities(self, evaluation_id: UUID) -> list[ReliabilityStateModel]:
        return list(
            self.db.scalars(
                select(ReliabilityStateModel)
                .where(ReliabilityStateModel.evaluation_id == evaluation_id)
                .order_by(ReliabilityStateModel.ticker)
            ).all()
        )

    def get_risk(self, evaluation_id: UUID) -> RiskStateModel | None:
        return self.db.scalar(
            select(RiskStateModel).where(RiskStateModel.evaluation_id == evaluation_id)
        )

    def get_signals(self, evaluation_id: UUID) -> list[ControlledSignalModel]:
        return list(
            self.db.scalars(
                select(ControlledSignalModel)
                .where(ControlledSignalModel.evaluation_id == evaluation_id)
                .order_by(ControlledSignalModel.ticker)
            ).all()
        )

    def get_signal_history(
        self,
        portfolio_id: str,
        ticker: str,
        before_date: date,
    ) -> list[ControlledSignalModel]:
        statement = (
            select(ControlledSignalModel)
            .join(EvaluationModel)
            .where(
                EvaluationModel.portfolio_id == portfolio_id,
                ControlledSignalModel.ticker == ticker,
                ControlledSignalModel.as_of_date < before_date,
            )
            .order_by(ControlledSignalModel.as_of_date)
        )
        return list(self.db.scalars(statement).all())
