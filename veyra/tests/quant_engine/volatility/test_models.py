"""Validation tests for Phase 3 volatility domain contracts."""

from datetime import date

import pytest
from pydantic import ValidationError

from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    MarketRegime,
    MarketVolatilityState,
    VolatilityEstimate,
)


def valid_parameters() -> GARCHParameters:
    return GARCHParameters(omega=0.000002, alpha=0.05, gamma=0.08, beta=0.85)


def valid_diagnostics(
    fit_status: GARCHFitStatus = GARCHFitStatus.SUCCESS,
) -> GARCHDiagnostics:
    return GARCHDiagnostics(
        fit_status=fit_status,
        convergence_status=GARCHConvergenceStatus.CONVERGED,
        observation_count=504,
        log_likelihood=1240.5,
    )


def test_valid_garch_parameters() -> None:
    parameters = valid_parameters()

    assert parameters.gamma == 0.08
    assert parameters.alpha + parameters.beta + parameters.gamma / 2 < 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("omega", 0.0),
        ("alpha", -0.01),
        ("beta", -0.01),
    ],
)
def test_garch_parameters_reject_invalid_bounds(field: str, value: float) -> None:
    values = {"omega": 0.000002, "alpha": 0.05, "gamma": 0.08, "beta": 0.85}
    values[field] = value

    with pytest.raises(ValidationError):
        GARCHParameters(**values)


def test_garch_parameters_allow_valid_negative_leverage_term() -> None:
    parameters = GARCHParameters(omega=0.000002, alpha=0.05, gamma=-0.02, beta=0.85)

    assert parameters.gamma == -0.02


@pytest.mark.parametrize(
    "values",
    [
        {"omega": 0.000002, "alpha": 0.05, "gamma": -0.06, "beta": 0.85},
        {"omega": 0.000002, "alpha": 0.10, "gamma": 0.10, "beta": 0.85},
    ],
)
def test_garch_parameters_reject_invalid_process_constraints(values: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        GARCHParameters(**values)


def test_garch_diagnostics_normalize_messages_and_isolate_defaults() -> None:
    first = valid_diagnostics()
    second = valid_diagnostics()
    first.warnings.append("optimizer near boundary")

    diagnostics = GARCHDiagnostics(
        fit_status=GARCHFitStatus.FALLBACK,
        convergence_status=GARCHConvergenceStatus.NOT_CONVERGED,
        observation_count=252,
        warnings=["  optimizer did not converge  "],
        errors=["  rolling-volatility fallback used  "],
    )

    assert second.warnings == []
    assert diagnostics.warnings == ["optimizer did not converge"]
    assert diagnostics.errors == ["rolling-volatility fallback used"]


@pytest.mark.parametrize("field", ["warnings", "errors"])
def test_garch_diagnostics_reject_empty_messages(field: str) -> None:
    values = {
        "fit_status": GARCHFitStatus.FAILED,
        "convergence_status": GARCHConvergenceStatus.NOT_APPLICABLE,
        "observation_count": 0,
        field: ["  "],
    }

    with pytest.raises(ValidationError, match="diagnostic messages must not be empty"):
        GARCHDiagnostics(**values)


def test_garch_diagnostics_reject_negative_observation_count() -> None:
    with pytest.raises(ValidationError):
        GARCHDiagnostics(
            fit_status=GARCHFitStatus.INSUFFICIENT_DATA,
            convergence_status=GARCHConvergenceStatus.NOT_APPLICABLE,
            observation_count=-1,
        )


def test_valid_volatility_estimate_normalizes_ticker() -> None:
    estimate = VolatilityEstimate(
        ticker=" aapl ",
        timestamp=date(2026, 9, 16),
        conditional_variance=0.0004,
        conditional_volatility=0.02,
        forecast_volatility=0.021,
        realized_volatility=0.018,
        volatility_ratio=0.02 / 0.018,
        parameters=valid_parameters(),
        diagnostics=valid_diagnostics(),
    )

    assert estimate.ticker == "AAPL"
    assert estimate.parameters is not None


def test_fallback_volatility_estimate_can_omit_parameters() -> None:
    estimate = VolatilityEstimate(
        ticker="MSFT",
        timestamp=date(2026, 9, 16),
        conditional_variance=0.0004,
        conditional_volatility=0.02,
        forecast_volatility=0.02,
        realized_volatility=0.018,
        volatility_ratio=0.02 / 0.018,
        diagnostics=valid_diagnostics(GARCHFitStatus.FALLBACK),
    )

    assert estimate.parameters is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("conditional_variance", -0.0004),
        ("conditional_volatility", -0.02),
        ("forecast_volatility", -0.02),
        ("realized_volatility", -0.02),
        ("volatility_ratio", -1.0),
        ("volatility_ratio", float("nan")),
    ],
)
def test_volatility_estimate_rejects_invalid_values(field: str, value: float) -> None:
    values = {
        "ticker": "AAPL",
        "timestamp": date(2026, 9, 16),
        "conditional_variance": 0.0004,
        "conditional_volatility": 0.02,
        "forecast_volatility": 0.021,
        "realized_volatility": 0.018,
        "volatility_ratio": 0.02 / 0.018,
        "parameters": valid_parameters(),
        "diagnostics": valid_diagnostics(),
    }
    values[field] = value

    with pytest.raises(ValidationError):
        VolatilityEstimate(**values)


def test_volatility_estimate_rejects_inconsistent_variance() -> None:
    with pytest.raises(ValidationError, match="conditional_variance must equal"):
        VolatilityEstimate(
            ticker="AAPL",
            timestamp=date(2026, 9, 16),
            conditional_variance=0.0005,
            conditional_volatility=0.02,
            forecast_volatility=0.021,
            realized_volatility=0.018,
            volatility_ratio=0.02 / 0.018,
            parameters=valid_parameters(),
            diagnostics=valid_diagnostics(),
        )


def test_successful_volatility_estimate_requires_parameters() -> None:
    with pytest.raises(ValidationError, match="parameters are required"):
        VolatilityEstimate(
            ticker="AAPL",
            timestamp=date(2026, 9, 16),
            conditional_variance=0.0004,
            conditional_volatility=0.02,
            forecast_volatility=0.021,
            realized_volatility=0.018,
            volatility_ratio=0.02 / 0.018,
            diagnostics=valid_diagnostics(),
        )


@pytest.mark.parametrize(
    ("stress_score", "threshold", "regime"),
    [
        (1.30, 1.20, MarketRegime.HIGH_STRESS),
        (1.20, 1.20, MarketRegime.HIGH_STRESS),
        (1.10, 1.20, MarketRegime.NORMAL),
    ],
)
def test_valid_market_volatility_regimes(
    stress_score: float,
    threshold: float,
    regime: MarketRegime,
) -> None:
    state = MarketVolatilityState(
        timestamp=date(2026, 9, 16),
        number_of_assets=150,
        aggregate_volatility=0.022,
        median_volatility_ratio=stress_score,
        stress_score=stress_score,
        threshold=threshold,
        regime=regime,
    )

    assert state.regime is regime


def test_market_volatility_state_rejects_empty_cross_section() -> None:
    with pytest.raises(ValidationError):
        MarketVolatilityState(
            timestamp=date(2026, 9, 16),
            number_of_assets=0,
            aggregate_volatility=0.0,
            median_volatility_ratio=0.0,
            stress_score=0.0,
            threshold=1.2,
            regime=MarketRegime.NORMAL,
        )


def test_market_volatility_state_rejects_regime_mismatch() -> None:
    with pytest.raises(ValidationError, match="regime must be HIGH_STRESS"):
        MarketVolatilityState(
            timestamp=date(2026, 9, 16),
            number_of_assets=150,
            aggregate_volatility=0.022,
            median_volatility_ratio=1.3,
            stress_score=1.3,
            threshold=1.2,
            regime=MarketRegime.NORMAL,
        )
