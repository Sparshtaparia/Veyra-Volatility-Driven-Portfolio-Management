"""Tests for the production GJR-GARCH(1,1) engine."""

from __future__ import annotations

import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import quant_engine.volatility.gjr_garch as gjr_garch_module
from quant_engine.volatility.exceptions import (
    GARCHConvergenceError,
    GARCHFitError,
    InsufficientHistoryError,
    InvalidReturnsError,
)
from quant_engine.volatility.gjr_garch import GJRGarchEngine
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHFitStatus,
    VolatilityEstimate,
)


@pytest.fixture(scope="module")
def asymmetric_returns() -> pd.Series:
    """Deterministic GJR process with clustered volatility and asymmetric shocks."""

    rng = np.random.default_rng(20260916)
    observation_count = 500
    variance = np.empty(observation_count)
    innovations = np.empty(observation_count)
    variance[0] = 0.0001
    innovations[0] = np.sqrt(variance[0]) * rng.normal()

    for position in range(1, observation_count):
        previous_shock = innovations[position - 1]
        variance[position] = (
            0.000002
            + 0.05 * previous_shock**2
            + 0.10 * (previous_shock < 0) * previous_shock**2
            + 0.87 * variance[position - 1]
        )
        innovations[position] = np.sqrt(variance[position]) * rng.normal()

    return pd.Series(
        innovations,
        index=pd.date_range("2020-01-01", periods=observation_count, freq="B"),
        name="return",
    )


@pytest.fixture(scope="module")
def fitted_estimate(asymmetric_returns: pd.Series) -> VolatilityEstimate:
    return GJRGarchEngine().fit("aapl", asymmetric_returns)


@pytest.fixture
def short_returns() -> pd.Series:
    values = np.sin(np.arange(80, dtype=float)) * 0.01
    return pd.Series(values, index=pd.date_range("2025-01-01", periods=80, freq="B"))


class FakeArchResult:
    def __init__(self, index: pd.Index, *, convergence_flag: int = 0) -> None:
        self.params = pd.Series(
            {
                "mu": 0.0,
                "omega": 0.04,
                "alpha[1]": 0.05,
                "gamma[1]": 0.10,
                "beta[1]": 0.80,
            }
        )
        self.conditional_volatility = pd.Series(2.0, index=index)
        self.convergence_flag = convergence_flag
        self.loglikelihood = -123.5

    @staticmethod
    def forecast(horizon: int, reindex: bool) -> SimpleNamespace:
        assert horizon == 1
        assert reindex is False
        return SimpleNamespace(variance=pd.DataFrame([[9.0]]))


def install_fake_arch(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[dict[str, object]],
    *,
    convergence_flag: int = 0,
    emitted_warning: str | None = None,
) -> None:
    class FakeArchModel:
        def __init__(self, series: pd.Series) -> None:
            self.series = series

        def fit(self, *, disp: str, show_warning: bool) -> FakeArchResult:
            calls[-1]["fit_kwargs"] = {"disp": disp, "show_warning": show_warning}
            if emitted_warning:
                warnings.warn(emitted_warning, UserWarning, stacklevel=2)
            return FakeArchResult(self.series.index, convergence_flag=convergence_flag)

    def fake_arch_model(series: pd.Series, **kwargs: object) -> FakeArchModel:
        calls.append({"returns": series.copy(), "model_kwargs": kwargs})
        return FakeArchModel(series)

    monkeypatch.setattr(gjr_garch_module, "arch_model", fake_arch_model)


def test_successful_fit_returns_valid_estimate(fitted_estimate: VolatilityEstimate) -> None:
    assert fitted_estimate.ticker == "AAPL"
    assert fitted_estimate.diagnostics.fit_status is GARCHFitStatus.SUCCESS
    assert fitted_estimate.diagnostics.convergence_status is GARCHConvergenceStatus.CONVERGED
    assert fitted_estimate.diagnostics.observation_count == 500
    assert np.isfinite(fitted_estimate.diagnostics.log_likelihood)


def test_fitted_parameters_are_finite_and_include_gamma(
    fitted_estimate: VolatilityEstimate,
) -> None:
    assert fitted_estimate.parameters is not None
    values = [
        fitted_estimate.parameters.omega,
        fitted_estimate.parameters.alpha,
        fitted_estimate.parameters.gamma,
        fitted_estimate.parameters.beta,
        fitted_estimate.parameters.persistence,
    ]
    assert all(np.isfinite(value) for value in values)


def test_conditional_and_forecast_volatility_are_valid(
    fitted_estimate: VolatilityEstimate,
) -> None:
    assert fitted_estimate.conditional_variance >= 0.0
    assert fitted_estimate.conditional_volatility >= 0.0
    assert fitted_estimate.conditional_volatility**2 == pytest.approx(
        fitted_estimate.conditional_variance
    )
    assert np.isfinite(fitted_estimate.forecast_volatility)
    assert fitted_estimate.forecast_volatility > 0.0


def test_asymmetric_model_specification_and_return_scaling(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    calls: list[dict[str, object]] = []
    install_fake_arch(monkeypatch, calls)

    estimate = GJRGarchEngine(min_observations=30).fit("msft", short_returns)

    call = calls[0]
    model_kwargs = call["model_kwargs"]
    assert isinstance(model_kwargs, dict)
    assert (model_kwargs["p"], model_kwargs["o"], model_kwargs["q"]) == (1, 1, 1)
    assert model_kwargs["mean"] == "Constant"
    assert model_kwargs["dist"] == "normal"
    assert model_kwargs["rescale"] is False
    pd.testing.assert_series_equal(call["returns"], short_returns * 100.0)

    assert estimate.conditional_volatility == pytest.approx(0.02)
    assert estimate.conditional_variance == pytest.approx(0.02**2)
    assert estimate.forecast_volatility == pytest.approx(0.03)
    assert estimate.parameters is not None
    assert estimate.parameters.omega == pytest.approx(0.04 / 100.0**2)


def test_realized_volatility_and_ratio_use_trailing_window(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    install_fake_arch(monkeypatch, [])
    engine = GJRGarchEngine(min_observations=30, realized_window=21)

    estimate = engine.fit("MSFT", short_returns)
    expected_realized = short_returns.iloc[-21:].std(ddof=1)

    assert estimate.realized_volatility == pytest.approx(expected_realized)
    assert estimate.volatility_ratio == pytest.approx(0.02 / expected_realized)


def test_ticker_and_as_of_timestamp_are_propagated(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    install_fake_arch(monkeypatch, [])
    as_of = short_returns.index[59]

    estimate = GJRGarchEngine(min_observations=30).fit("  nvda  ", short_returns, as_of)

    assert estimate.ticker == "NVDA"
    assert estimate.timestamp == as_of.date()
    assert estimate.diagnostics.observation_count == 60


def test_nan_values_are_dropped_and_reported(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    install_fake_arch(monkeypatch, [])
    returns = short_returns.copy()
    returns.iloc[[2, 10]] = np.nan

    estimate = GJRGarchEngine(min_observations=30).fit("AAPL", returns)

    assert estimate.diagnostics.observation_count == len(returns) - 2
    assert estimate.diagnostics.warnings == [
        "Dropped 2 NaN return observation(s); values were not forward-filled"
    ]


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series(dtype=float, index=pd.DatetimeIndex([])),
        pd.Series(np.nan, index=pd.date_range("2025-01-01", periods=40, freq="B")),
    ],
)
def test_empty_or_all_nan_returns_are_rejected(returns: pd.Series) -> None:
    with pytest.raises(InvalidReturnsError):
        GJRGarchEngine(min_observations=30).fit("AAPL", returns)


def test_infinite_returns_are_rejected(short_returns: pd.Series) -> None:
    returns = short_returns.copy()
    returns.iloc[5] = np.inf

    with pytest.raises(InvalidReturnsError, match="infinite"):
        GJRGarchEngine(min_observations=30).fit("AAPL", returns)


def test_insufficient_history_is_rejected(short_returns: pd.Series) -> None:
    with pytest.raises(InsufficientHistoryError) as error:
        GJRGarchEngine(min_observations=60).fit("AAPL", short_returns.iloc[:40])

    assert error.value.observation_count == 40
    assert error.value.minimum_required == 60


def test_constant_and_nearly_constant_returns_are_rejected() -> None:
    index = pd.date_range("2025-01-01", periods=40, freq="B")
    constant = pd.Series(0.001, index=index)
    nearly_constant = pd.Series(0.001 + np.arange(40) * 1e-10, index=index)
    engine = GJRGarchEngine(min_observations=30, variance_tolerance=1e-12)

    with pytest.raises(InvalidReturnsError, match="constant or nearly constant"):
        engine.fit("AAPL", constant)
    with pytest.raises(InvalidReturnsError, match="constant or nearly constant"):
        engine.fit("AAPL", nearly_constant)


def test_non_chronological_and_duplicate_timestamps_are_rejected(
    short_returns: pd.Series,
) -> None:
    non_chronological = short_returns.iloc[::-1]
    duplicate = pd.concat([short_returns, short_returns.iloc[[-1]]])

    with pytest.raises(InvalidReturnsError, match="chronological"):
        GJRGarchEngine(min_observations=30).fit("AAPL", non_chronological)
    with pytest.raises(InvalidReturnsError, match="duplicate"):
        GJRGarchEngine(min_observations=30).fit("AAPL", duplicate)


def test_non_numeric_returns_are_rejected() -> None:
    returns = pd.Series(
        ["0.01"] * 40,
        index=pd.date_range("2025-01-01", periods=40, freq="B"),
    )

    with pytest.raises(InvalidReturnsError, match="numerical"):
        GJRGarchEngine(min_observations=30).fit("AAPL", returns)


def test_optimizer_warnings_are_captured_not_printed(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    install_fake_arch(monkeypatch, [], emitted_warning="optimizer near boundary")

    with warnings.catch_warnings(record=True) as escaped_warnings:
        estimate = GJRGarchEngine(min_observations=30).fit("AAPL", short_returns)

    assert escaped_warnings == []
    assert estimate.diagnostics.warnings == ["optimizer near boundary"]


def test_non_convergence_returns_diagnostic_fallback(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    install_fake_arch(monkeypatch, [], convergence_flag=4)

    estimate = GJRGarchEngine(min_observations=30).fit("AAPL", short_returns)

    assert estimate.diagnostics.fit_status is GARCHFitStatus.FALLBACK
    assert estimate.diagnostics.convergence_status is GARCHConvergenceStatus.NOT_CONVERGED
    assert estimate.diagnostics.errors
    assert estimate.parameters is None
    assert estimate.volatility_ratio == 1.0


def test_fit_failure_returns_fallback_without_leaking_third_party_exception(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    class ThirdPartyFailure(Exception):
        pass

    def failing_arch_model(*args: object, **kwargs: object) -> object:
        raise ThirdPartyFailure("optimizer exploded")

    monkeypatch.setattr(gjr_garch_module, "arch_model", failing_arch_model)
    estimate = GJRGarchEngine(min_observations=30).fit("AAPL", short_returns)

    assert isinstance(estimate, VolatilityEstimate)
    assert estimate.diagnostics.fit_status is GARCHFitStatus.FALLBACK
    assert "optimizer exploded" in estimate.diagnostics.errors[0]
    assert not hasattr(estimate, "arch_result")


def test_strict_failure_mode_raises_chained_domain_exception(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    class ThirdPartyFailure(Exception):
        pass

    def failing_arch_model(*args: object, **kwargs: object) -> object:
        raise ThirdPartyFailure("optimizer exploded")

    monkeypatch.setattr(gjr_garch_module, "arch_model", failing_arch_model)
    engine = GJRGarchEngine(min_observations=30, fallback_on_failure=False)

    with pytest.raises(GARCHFitError) as error:
        engine.fit("AAPL", short_returns)

    assert isinstance(error.value.__cause__, ThirdPartyFailure)


def test_strict_non_convergence_raises_domain_exception(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    install_fake_arch(monkeypatch, [], convergence_flag=1)
    engine = GJRGarchEngine(min_observations=30, fallback_on_failure=False)

    with pytest.raises(GARCHConvergenceError):
        engine.fit("AAPL", short_returns)


def test_future_observations_do_not_change_as_of_estimate(
    monkeypatch: pytest.MonkeyPatch,
    short_returns: pd.Series,
) -> None:
    calls: list[dict[str, object]] = []
    install_fake_arch(monkeypatch, calls)
    engine = GJRGarchEngine(min_observations=30)
    as_of = short_returns.index[59]

    baseline = engine.fit("AAPL", short_returns, as_of)
    mutated = short_returns.copy()
    mutated.loc[mutated.index > as_of] = 10.0
    recomputed = engine.fit("AAPL", mutated, as_of)

    pd.testing.assert_series_equal(calls[0]["returns"], calls[1]["returns"])
    assert recomputed == baseline


def test_default_history_and_model_order_match_research_methodology() -> None:
    engine = GJRGarchEngine()

    assert engine.min_observations == 252
    assert engine.realized_window == 21
    assert engine.MODEL_ORDER == (1, 1, 1)
