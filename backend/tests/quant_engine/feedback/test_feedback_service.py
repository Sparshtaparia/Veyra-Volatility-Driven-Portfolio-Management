"""
Phase 8 Unit Tests: Feedback Engine & Adaptive Threshold
=========================================================

Tests cover:
- feedback_error calculation
- threshold update formula
- threshold lower bound enforcement
- threshold upper bound enforcement
- zero feedback_error case
- deterministic output (same inputs → same outputs)
- invalid eta
- invalid min/max_threshold combination
- invalid observed_volatility
- FeedbackCycle model validation
"""
import pytest
from datetime import date
from uuid import uuid4

from quant_engine.feedback.service import FeedbackService
from quant_engine.feedback.models import FeedbackCycle


EVALUATION_ID = uuid4()
PORTFOLIO_ID = "portfolio_test_001"
TODAY = date.today()


# ---------------------------------------------------------------------------
# 1. Feedback error calculation
# ---------------------------------------------------------------------------

def test_feedback_error_positive():
    svc = FeedbackService()
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.10, observed_volatility=0.15, observation_date=TODAY)
    # error = 0.15 - 0.10 = 0.05
    assert cycle.feedback_error == pytest.approx(0.05)

def test_feedback_error_negative():
    svc = FeedbackService()
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.20, observed_volatility=0.10, observation_date=TODAY)
    # error = 0.10 - 0.20 = -0.10
    assert cycle.feedback_error == pytest.approx(-0.10)


# ---------------------------------------------------------------------------
# 2. Threshold update formula
# ---------------------------------------------------------------------------

def test_threshold_update_formula():
    svc = FeedbackService(eta=0.1)
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.10, observed_volatility=0.20, observation_date=TODAY)
    # updated = clip(0.10 + 0.1 * 0.10, 0.01, 1.0) = clip(0.11, 0.01, 1.0) = 0.11
    assert cycle.updated_threshold == pytest.approx(0.11)

def test_threshold_update_formula_decrease():
    svc = FeedbackService(eta=0.2)
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.30, observed_volatility=0.10, observation_date=TODAY)
    # updated = clip(0.30 + 0.2 * (-0.20), 0.01, 1.0) = clip(0.30 - 0.04, 0.01, 1.0) = 0.26
    assert cycle.updated_threshold == pytest.approx(0.26)


# ---------------------------------------------------------------------------
# 3. Threshold lower bound
# ---------------------------------------------------------------------------

def test_threshold_lower_bound_enforced():
    svc = FeedbackService(eta=1.0, min_threshold=0.05)
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.05, observed_volatility=0.0, observation_date=TODAY)
    # raw = 0.05 + 1.0 * (0.0 - 0.05) = 0.0 → clipped to 0.05
    assert cycle.updated_threshold >= 0.05


# ---------------------------------------------------------------------------
# 4. Threshold upper bound
# ---------------------------------------------------------------------------

def test_threshold_upper_bound_enforced():
    svc = FeedbackService(eta=1.0, max_threshold=0.50)
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.40, observed_volatility=0.80, observation_date=TODAY)
    # raw = 0.40 + 1.0 * 0.40 = 0.80 → clipped to 0.50
    assert cycle.updated_threshold == pytest.approx(0.50)


# ---------------------------------------------------------------------------
# 5. Zero feedback error
# ---------------------------------------------------------------------------

def test_zero_feedback_error():
    svc = FeedbackService(eta=0.1)
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.15, observed_volatility=0.15, observation_date=TODAY)
    assert cycle.feedback_error == 0.0
    # No change when error is zero
    assert cycle.updated_threshold == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# 6. Deterministic output
# ---------------------------------------------------------------------------

def test_deterministic_output():
    svc = FeedbackService(eta=0.1)
    c1 = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.12, observed_volatility=0.18, observation_date=TODAY)
    c2 = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.12, observed_volatility=0.18, observation_date=TODAY)
    assert c1.feedback_error == c2.feedback_error
    assert c1.updated_threshold == c2.updated_threshold


# ---------------------------------------------------------------------------
# 7. Invalid eta
# ---------------------------------------------------------------------------

def test_invalid_eta_negative():
    with pytest.raises(ValueError, match="eta"):
        FeedbackService(eta=-0.1)

def test_invalid_eta_too_large():
    with pytest.raises(ValueError, match="eta"):
        FeedbackService(eta=1.5)


# ---------------------------------------------------------------------------
# 8. Invalid threshold bounds
# ---------------------------------------------------------------------------

def test_invalid_threshold_min_greater_than_max():
    with pytest.raises(ValueError, match="min_threshold"):
        FeedbackService(min_threshold=0.5, max_threshold=0.2)

def test_invalid_threshold_min_not_positive():
    with pytest.raises(ValueError, match="min_threshold"):
        FeedbackService(min_threshold=0.0)


# ---------------------------------------------------------------------------
# 9. Invalid inputs to calculate_feedback
# ---------------------------------------------------------------------------

def test_negative_previous_threshold():
    svc = FeedbackService()
    with pytest.raises(ValueError, match="previous_threshold"):
        svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=-0.05, observed_volatility=0.10, observation_date=TODAY)

def test_negative_observed_volatility():
    svc = FeedbackService()
    with pytest.raises(ValueError, match="observed_volatility"):
        svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.10, observed_volatility=-0.05, observation_date=TODAY)


# ---------------------------------------------------------------------------
# 10. FeedbackCycle model fields
# ---------------------------------------------------------------------------

def test_feedback_cycle_has_all_required_fields():
    svc = FeedbackService(eta=0.1)
    cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=0.10, observed_volatility=0.12, observation_date=TODAY)
    assert cycle.evaluation_id == EVALUATION_ID
    assert cycle.portfolio_id == PORTFOLIO_ID
    assert cycle.previous_threshold == pytest.approx(0.10)
    assert cycle.observed_volatility == pytest.approx(0.12)
    # feedback_error = 0.12 - 0.10 = 0.02
    assert cycle.feedback_error == pytest.approx(0.02)
    # updated_threshold = clip(0.10 + 0.1 * 0.02, 0.01, 1.0) = 0.102
    assert cycle.updated_threshold == pytest.approx(0.102)
    assert cycle.timestamp == TODAY


# ---------------------------------------------------------------------------
# 11. Bounds always satisfied for many random inputs
# ---------------------------------------------------------------------------

def test_bounds_always_satisfied():
    svc = FeedbackService(eta=0.5, min_threshold=0.02, max_threshold=0.30)
    test_cases = [
        (0.02, 0.00),
        (0.30, 1.00),
        (0.15, 0.50),
        (0.01, 0.01),
        (0.50, 0.50),
    ]
    for prev, obs in test_cases:
        # prev may be clamped by pydantic to be >=0 but keep test within valid range
        p = max(0.01, prev)
        cycle = svc.calculate_feedback(EVALUATION_ID, PORTFOLIO_ID, previous_threshold=p, observed_volatility=max(0.0, obs), observation_date=TODAY)
        assert cycle.updated_threshold >= 0.02, f"below min for prev={p}, obs={obs}"
        assert cycle.updated_threshold <= 0.30, f"above max for prev={p}, obs={obs}"
