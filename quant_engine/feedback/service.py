from datetime import date
from uuid import UUID

from quant_engine.feedback.models import FeedbackCycle


class FeedbackService:
    """
    Phase 8 Feedback Engine.
    Closes the loop by calculating an adaptive threshold for the next evaluation.
    """

    def __init__(self, eta: float = 0.1, min_threshold: float = 0.01, max_threshold: float = 1.0):
        if not (0 <= eta <= 1):
            raise ValueError("eta must be between 0 and 1")
        if min_threshold >= max_threshold:
            raise ValueError("min_threshold must be strictly less than max_threshold")
        if min_threshold <= 0:
            raise ValueError("min_threshold must be positive")
            
        self.eta = eta
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold

    def calculate_feedback(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        previous_threshold: float,
        observed_volatility: float,
        observation_date: date
    ) -> FeedbackCycle:
        if previous_threshold < 0:
            raise ValueError("previous_threshold must be non-negative")
        if observed_volatility < 0:
            raise ValueError("observed_volatility must be non-negative")

        feedback_error = observed_volatility - previous_threshold
        
        raw_updated_threshold = previous_threshold + (self.eta * feedback_error)
        updated_threshold = max(self.min_threshold, min(self.max_threshold, raw_updated_threshold))
        
        return FeedbackCycle(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            previous_threshold=previous_threshold,
            observed_volatility=observed_volatility,
            feedback_error=feedback_error,
            updated_threshold=updated_threshold,
            timestamp=observation_date
        )
