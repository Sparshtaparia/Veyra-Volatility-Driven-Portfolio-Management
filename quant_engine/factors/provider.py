"""Provider boundary for historical Fama-French returns."""

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

import pandas as pd

REQUIRED_FACTOR_COLUMNS = ("MKT-RF", "SMB", "HML", "RMW", "CMA", "RF")


class FactorDataProvider(ABC):
    @abstractmethod
    def get_history(self, start_date: date, end_date: date) -> pd.DataFrame: ...


class CSVFactorDataProvider(FactorDataProvider):
    """Read a locally managed decimal-return factor file with a date column."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def get_history(self, start_date: date, end_date: date) -> pd.DataFrame:
        if not self.path.is_file():
            raise FileNotFoundError(
                f"Fama-French data file not found: {self.path}. "
                "Run `python -m quant_engine.factors.setup` to download the official dataset."
            )
        frame = pd.read_csv(self.path)
        date_column = next((column for column in frame.columns if column.lower() == "date"), None)
        if date_column is None:
            raise ValueError("factor CSV must contain a date column")
        frame.index = pd.to_datetime(frame.pop(date_column), errors="coerce")
        validated = validate_factor_frame(frame)
        validated.index = frame.index
        if validated.index.isna().any() or validated.index.has_duplicates:
            raise ValueError("factor CSV dates must be valid and unique")
        return validated.loc[
            (frame.index >= pd.Timestamp(start_date)) & (frame.index <= pd.Timestamp(end_date))
        ].sort_index()


def validate_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate canonical five-factor daily data without changing its scale."""
    aliases = {column.upper().replace("_", "-"): column for column in frame.columns}
    missing = [column for column in REQUIRED_FACTOR_COLUMNS if column not in aliases]
    if missing:
        raise ValueError(f"missing Fama-French columns: {', '.join(missing)}")
    normalized = frame[[aliases[column] for column in REQUIRED_FACTOR_COLUMNS]].copy()
    normalized.columns = list(REQUIRED_FACTOR_COLUMNS)
    for column in REQUIRED_FACTOR_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    if normalized.empty or normalized.isna().any().any():
        raise ValueError("factor CSV contains empty or non-numeric factor values")
    return normalized
