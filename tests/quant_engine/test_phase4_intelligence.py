"""Phase 4 quantitative intelligence tests."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quant_engine.factors.fama_french import FACTOR_COLUMNS, FamaFrenchEstimator
from quant_engine.factors.models import (
    FactorSnapshot,
    NormalizationMethod,
    SignalConfig,
)
from quant_engine.factors.normalization import normalize_cross_section
from quant_engine.factors.signal import BaseSignalEngine
from quant_engine.reliability.engine import ReliabilityEngine
from quant_engine.risk.engine import RiskStateEngine
from quant_engine.risk.models import RiskConfig
from quant_engine.signals.models import OperatorConfig
from quant_engine.signals.operator import StateCoupledOperator
from quant_engine.volatility.models import MarketRegime


def regression_data(periods: int = 100):
    index = pd.date_range("2025-01-01", periods=periods, freq="D")
    generator = np.random.default_rng(7)
    factors = pd.DataFrame(
        generator.normal(0.0, 0.01, (periods, 5)), index=index, columns=FACTOR_COLUMNS
    )
    factors["RF"] = 0.0001
    coefficients = np.array([1.1, 0.2, -0.3, 0.4, 0.1])
    asset = pd.Series(
        0.0005 + factors[list(FACTOR_COLUMNS)].to_numpy() @ coefficients + factors["RF"],
        index=index,
    )
    return asset, factors


def test_fama_french_recovers_exposures() -> None:
    asset, factors = regression_data()
    result = FamaFrenchEstimator(window=80, minimum_observations=60).estimate(
        "aapl", asset, factors, date(2025, 4, 10)
    )
    assert result.alpha == pytest.approx(0.0005)
    assert result.market_beta == pytest.approx(1.1)
    assert result.smb_beta == pytest.approx(0.2)
    assert result.hml_beta == pytest.approx(-0.3)
    assert result.r_squared == pytest.approx(1.0)
    assert result.observation_count == 80


def test_fama_french_has_no_lookahead() -> None:
    asset, factors = regression_data()
    estimator = FamaFrenchEstimator(window=80, minimum_observations=60)
    cutoff = date(2025, 3, 31)
    baseline = estimator.estimate("AAPL", asset, factors, cutoff)
    asset.loc[asset.index > pd.Timestamp(cutoff)] = 99.0
    factors.loc[factors.index > pd.Timestamp(cutoff), :] = -99.0
    changed = estimator.estimate("AAPL", asset, factors, cutoff)
    assert changed == baseline


def test_z_score_normalization_is_cross_sectional() -> None:
    normalized = normalize_cross_section(
        {"A": {"alpha": 1.0}, "B": {"alpha": 2.0}, "C": {"alpha": 3.0}}
    )
    values = [normalized[ticker]["alpha"] for ticker in sorted(normalized)]
    assert np.mean(values) == pytest.approx(0.0)
    assert np.std(values) == pytest.approx(1.0)


def test_rank_normalization_is_supported() -> None:
    normalized = normalize_cross_section(
        {"A": {"alpha": 3.0}, "B": {"alpha": 1.0}, "C": {"alpha": 2.0}},
        NormalizationMethod.PERCENTILE_RANK,
    )
    assert normalized == {"A": {"alpha": 1.0}, "B": {"alpha": -1.0}, "C": {"alpha": 0.0}}


def test_base_signal_exposes_factor_contributions() -> None:
    snapshot = FactorSnapshot(
        ticker="AAPL",
        as_of_date=date(2026, 1, 1),
        raw_factors={"alpha": 0.2, "momentum": 1.0},
        normalized_factors={"alpha": 1.0, "momentum": -0.5},
        normalization_method=NormalizationMethod.Z_SCORE,
    )
    result = BaseSignalEngine(SignalConfig(weights={"alpha": 0.6, "momentum": 0.4})).calculate(
        snapshot
    )
    assert result.contributions == {"alpha": 0.6, "momentum": -0.2}
    assert result.base_signal == pytest.approx(0.4)


def test_reliability_is_volatility_and_regime_conditioned() -> None:
    engine = ReliabilityEngine()
    normal = engine.calculate(
        "AAPL", date(2026, 1, 1), r_squared=0.8, volatility_ratio=1.0, regime=MarketRegime.NORMAL
    )
    stressed = engine.calculate(
        "AAPL",
        date(2026, 1, 1),
        r_squared=0.8,
        volatility_ratio=2.0,
        regime=MarketRegime.HIGH_STRESS,
    )
    assert stressed.effective_reliability < normal.effective_reliability
    assert normal.base_reliability == 0.8


def test_recent_performance_adjusts_reliability() -> None:
    engine = ReliabilityEngine()
    positive = engine.calculate(
        "A",
        date(2026, 1, 1),
        r_squared=0.8,
        volatility_ratio=1.0,
        regime=MarketRegime.NORMAL,
        recent_performance_score=1.0,
    )
    negative = engine.calculate(
        "A",
        date(2026, 1, 1),
        r_squared=0.8,
        volatility_ratio=1.0,
        regime=MarketRegime.NORMAL,
        recent_performance_score=-1.0,
    )
    assert positive.effective_reliability > negative.effective_reliability


def test_risk_state_keeps_components_visible() -> None:
    index = pd.date_range("2025-01-01", periods=20, freq="D")
    history = {
        "A": pd.Series(np.full(20, 0.01), index=index),
        "B": pd.Series(np.full(20, 0.008), index=index),
    }
    result = RiskStateEngine(RiskConfig(liquidity_reference=1_000.0)).calculate(
        date(2025, 1, 20),
        weights={"A": 0.6, "B": 0.4},
        conditional_volatility={"A": 0.02, "B": 0.03},
        return_history=history,
        dollar_volume={"A": 2_000.0, "B": 500.0},
    )
    assert result.volatility_risk == pytest.approx(0.6)
    assert result.concentration_risk == pytest.approx(0.52)
    assert 0.0 <= result.composite_risk <= 1.0


def test_state_coupled_operator_formula_is_explicit() -> None:
    result = StateCoupledOperator(OperatorConfig(risk_aversion=1.0)).apply(
        "AAPL",
        date(2026, 1, 1),
        base_signal=0.8,
        volatility_adjustment=0.5,
        reliability_adjustment=0.75,
        composite_risk=0.2,
    )
    assert result.risk_adjustment == pytest.approx(0.8)
    assert result.controlled_signal == pytest.approx(0.24)
