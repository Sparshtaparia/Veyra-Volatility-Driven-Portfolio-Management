"""Fama-French data-provider dependency."""

from backend.exceptions import FactorDataUnavailableError
from config.settings import get_settings
from quant_engine.factors.provider import CSVFactorDataProvider, FactorDataProvider


class _UnconfiguredFactorDataProvider(FactorDataProvider):
    def get_history(self, start_date, end_date):
        raise FactorDataUnavailableError("FAMA_FRENCH_DATA_PATH is not configured")


def get_factor_data_provider() -> FactorDataProvider:
    path = get_settings().fama_french_data_path
    if not path:
        return _UnconfiguredFactorDataProvider()
    return CSVFactorDataProvider(path)
