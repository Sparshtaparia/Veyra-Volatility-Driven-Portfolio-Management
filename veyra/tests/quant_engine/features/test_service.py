"""
tests/quant_engine/features/test_service.py
===========================================
Integration tests for FeatureService.
"""

from datetime import date
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MockProvider
from quant_engine.features.service import FeatureService

def test_feature_service_integration():
    # Create 70 days of mock data to satisfy the 60 day requirement
    bars = []
    for i in range(70):
        bars.append(
            MarketBar(
                ticker="AAPL",
                timestamp=date(2023, 1, 1).replace(day=(i%28)+1, month=(i//28)+1),
                open=150.0 + i,
                high=155.0 + i,
                low=149.0 + i,
                close=154.0 + i,
                volume=1000000
            )
        )
    
    provider = MockProvider(data=bars)
    service = FeatureService(provider=provider)
    
    snapshots = service.generate_features("AAPL", date(2023, 1, 1), date(2023, 12, 31))
    
    assert len(snapshots) == 70
    assert snapshots[0].ticker == "AAPL"
    
    # Last snapshot should have all features populated
    last = snapshots[-1]
    assert last.rsi is not None
    assert last.atr is not None
    assert last.macd_histogram is not None
    assert last.bollinger_band_width is not None
    assert last.dollar_volume is not None
