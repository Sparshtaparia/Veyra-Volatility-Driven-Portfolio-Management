"""Analytics Service to compute portfolio dashboard metrics."""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.schemas.analytics import (
    AnalyticsDashboardResponse,
    PerformanceStats,
    RiskAssessment,
    RiskScoreComponent,
    ConcentrationMetrics,
    SnapshotDataPoint,
    RecentDecision,
    AdaptiveThresholdState,
    DataStats
)
from database.models import (
    PortfolioModel,
    HoldingModel,
    RiskStateModel,
    PortfolioSnapshotModel,
    RebalanceEventModel,
    PortfolioTargetModel,
    FeedbackUpdateModel,
    EvaluationModel,
    TradeModel
)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(self, portfolio_id: str) -> AnalyticsDashboardResponse:
        portfolio = self.db.query(PortfolioModel).filter_by(id=portfolio_id).first()
        if not portfolio:
            raise ValueError("Portfolio not found")

        holdings = self.db.query(HoldingModel).filter_by(portfolio_id=portfolio_id).all()
        
        # 1. Performance
        portfolio_value = portfolio.total_value
        invested_amount = sum(h.average_price * h.quantity for h in holdings)
        absolute_return = portfolio_value - invested_amount
        return_percentage = (absolute_return / invested_amount * 100) if invested_amount > 0 else None

        performance = PerformanceStats(
            portfolio_value=portfolio_value,
            invested_amount=invested_amount,
            absolute_return=absolute_return,
            return_percentage=return_percentage
        )

        # 2. Risk Assessment
        latest_risk = self.db.query(RiskStateModel).filter_by(portfolio_id=portfolio_id).order_by(desc(RiskStateModel.as_of_date)).first()
        if latest_risk:
            score = int(latest_risk.composite_risk * 100)
            if score < 33:
                label = "Low"
            elif score < 66:
                label = "Moderate"
            else:
                label = "High"

            components = {
                "volatility": RiskScoreComponent(score=int(latest_risk.volatility_risk * 100), label="Volatility"),
                "concentration": RiskScoreComponent(score=int(latest_risk.concentration_risk * 100), label="Concentration"),
                "drawdown": RiskScoreComponent(score=int(latest_risk.drawdown_risk * 100), label="Drawdown"),
                "correlation": RiskScoreComponent(score=int(latest_risk.correlation_risk * 100), label="Correlation")
            }
            
            exps = []
            if latest_risk.concentration_risk > 0.5:
                exps.append("High single-stock exposure.")
            if latest_risk.volatility_risk > 0.5:
                exps.append("Elevated portfolio volatility.")
            if latest_risk.drawdown_risk > 0.5:
                exps.append("Significant historical drawdown.")
            if not exps:
                exps.append("Well-balanced portfolio across risk dimensions.")

            risk_assessment = RiskAssessment(
                overall_score=score,
                label=label,
                components=components,
                explanations=exps
            )
        else:
            risk_assessment = None

        # 3. Concentration
        weights = sorted([h.weight for h in holdings], reverse=True)
        largest = weights[0] if weights else None
        top_3 = sum(weights[:3]) if weights else None
        hhi = sum(w * w for w in weights) if weights else None

        concentration = ConcentrationMetrics(
            largest_position=largest,
            top_3=top_3,
            hhi=hhi
        )

        # 4. Snapshots & Drawdown
        snapshots = self.db.query(PortfolioSnapshotModel).filter_by(portfolio_id=portfolio_id).order_by(PortfolioSnapshotModel.snapshot_date).all()
        history = []
        max_drawdown = 0.0
        peak = 0.0
        for s in snapshots:
            history.append(SnapshotDataPoint(date=s.snapshot_date.isoformat(), portfolio_value=s.portfolio_value))
            if s.portfolio_value > peak:
                peak = s.portfolio_value
            if peak > 0:
                dd = (s.portfolio_value - peak) / peak
                if dd < max_drawdown:
                    max_drawdown = dd
        
        if not history and portfolio_value > 0:
            history.append(SnapshotDataPoint(date=portfolio.created_at.date().isoformat(), portfolio_value=portfolio_value))

        # 5. Volatility (approx from RiskState)
        volatility = latest_risk.volatility_risk if latest_risk else None

        # 6. Recent Decisions
        targets = self.db.query(PortfolioTargetModel).filter_by(portfolio_id=portfolio_id).filter(PortfolioTargetModel.weight_change != 0).order_by(desc(PortfolioTargetModel.created_at)).limit(10).all()
        decisions = []
        for t in targets:
            action = "Increased" if t.weight_change > 0 else "Reduced"
            decisions.append(RecentDecision(
                date=t.as_of_date.isoformat(),
                action=action,
                asset=t.ticker,
                weight_change=t.weight_change,
                reason=f"Target weight adjusted to {t.target_weight*100:.1f}%"
            ))

        # 7. Adaptive Threshold
        latest_feedback = self.db.query(FeedbackUpdateModel).filter_by(portfolio_id=portfolio_id).order_by(desc(FeedbackUpdateModel.observation_date)).first()
        if latest_feedback:
            adaptive = AdaptiveThresholdState(
                previous=float(latest_feedback.previous_state.get("volatility_threshold", 0)),
                observed=float(latest_feedback.observed_outcome.get("realized_volatility", 0)),
                updated=float(latest_feedback.updated_state.get("volatility_threshold", 0)),
                change=float(latest_feedback.updated_state.get("volatility_threshold", 0)) - float(latest_feedback.previous_state.get("volatility_threshold", 0))
            )
        else:
            adaptive = None

        # 8. Data Stats
        stats = DataStats(
            portfolio_valuations=len(snapshots),
            holdings=len(holdings),
            transactions=self.db.query(TradeModel).join(RebalanceEventModel).filter(RebalanceEventModel.portfolio_id == portfolio_id).count(),
            rebalance_evaluations=self.db.query(EvaluationModel).filter_by(portfolio_id=portfolio_id).count(),
            history_days=(datetime.utcnow().date() - portfolio.created_at.date()).days,
            last_updated=portfolio.updated_at
        )

        return AnalyticsDashboardResponse(
            portfolio_id=portfolio_id,
            performance=performance,
            risk_assessment=risk_assessment,
            concentration=concentration,
            volatility=volatility,
            max_drawdown=max_drawdown if max_drawdown < 0 else None,
            performance_history=history,
            recent_decisions=decisions,
            adaptive_threshold=adaptive,
            data_stats=stats
        )
