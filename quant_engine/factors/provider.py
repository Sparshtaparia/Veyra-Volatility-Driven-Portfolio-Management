"""Provider boundary for historical Fama-French returns."""

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

import pandas as pd


class FactorDataProvider(ABC):
    @abstractmethod
    def get_history(self, start_date: date, end_date: date) -> pd.DataFrame: ...


class CSVFactorDataProvider(FactorDataProvider):
    """Read a locally managed decimal-return factor file with a date column."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def get_history(self, start_date: date, end_date: date) -> pd.DataFrame:
        frame = pd.read_csv(self.path)
        date_column = next((column for column in frame.columns if column.lower() == "date"), None)
        if date_column is None:
            raise ValueError("factor CSV must contain a date column")
        frame.index = pd.to_datetime(frame.pop(date_column))
        return frame.loc[
            (frame.index >= pd.Timestamp(start_date)) & (frame.index <= pd.Timestamp(end_date))
        ].sort_index()
