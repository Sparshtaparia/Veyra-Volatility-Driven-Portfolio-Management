"""Official Fama-French setup and validation tests."""

import io
import zipfile

import pandas as pd

from quant_engine.factors.provider import CSVFactorDataProvider
from quant_engine.factors.setup import _parse_official_archive


def _official_archive() -> bytes:
    content = (
        "Official daily factors\n\n,Mkt-RF,SMB,HML,RMW,CMA,RF\n"
        "20260102,1.00,0.20,-0.10,0.05,0.03,0.01\n"
        "20260103,-0.50,0.10,0.20,0.00,-0.02,0.01\n\nAnnual Factors:\n"
    )
    destination = io.BytesIO()
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("F-F_Research_Data_5_Factors_2x3_daily.csv", content)
    return destination.getvalue()


def test_official_archive_is_normalized_to_decimal_daily_returns(tmp_path) -> None:
    frame = _parse_official_archive(_official_archive())
    assert list(frame.columns) == ["MKT-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert frame.loc[pd.Timestamp("2026-01-02"), "MKT-RF"] == 0.01

    path = tmp_path / "factors.csv"
    frame.to_csv(path, index_label="date")
    loaded = CSVFactorDataProvider(str(path)).get_history(
        pd.Timestamp("2026-01-02").date(), pd.Timestamp("2026-01-03").date()
    )
    assert loaded.equals(frame)


def test_factor_csv_rejects_missing_required_columns(tmp_path) -> None:
    path = tmp_path / "invalid.csv"
    pd.DataFrame({"date": ["2026-01-02"], "Mkt-RF": [0.01]}).to_csv(path, index=False)
    try:
        CSVFactorDataProvider(str(path)).get_history(
            pd.Timestamp("2026-01-02").date(), pd.Timestamp("2026-01-02").date()
        )
    except ValueError as exc:
        assert "missing Fama-French columns" in str(exc)
    else:
        raise AssertionError("invalid factor data was accepted")
