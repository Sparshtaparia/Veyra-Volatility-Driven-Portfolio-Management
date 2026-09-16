"""Fama-French data-provider dependency."""

from pathlib import Path

from backend.exceptions import FactorDataUnavailableError
from config.settings import get_settings
from quant_engine.factors.provider import CSVFactorDataProvider, FactorDataProvider


class _UnconfiguredFactorDataProvider(FactorDataProvider):
    def get_history(self, start_date, end_date):
        raise FactorDataUnavailableError(
            "Fama-French data is unavailable; run `python -m quant_engine.factors.setup`"
        )


def get_factor_data_provider() -> FactorDataProvider:
    path = get_settings().fama_french_data_path
    if not Path(path).is_file():
        return _UnconfiguredFactorDataProvider()
    return CSVFactorDataProvider(path)
