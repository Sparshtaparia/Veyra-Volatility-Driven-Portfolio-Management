"""Operational resilience around the existing market-data provider contract."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import date, timedelta

from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MarketDataProvider

logger = logging.getLogger("veyra.market_data")


class MarketDataOperationalError(RuntimeError):
    """Base error raised by the operational provider wrapper."""


class MarketDataTimeoutError(MarketDataOperationalError):
    pass


class MarketDataRateLimitError(MarketDataOperationalError):
    pass


class StaleMarketDataError(MarketDataOperationalError):
    pass


@dataclass(frozen=True)
class ProviderPolicy:
    attempts: int = 3
    base_backoff_seconds: float = 0.25
    max_backoff_seconds: float = 4.0
    timeout_seconds: float = 20.0
    requests_per_second: float = 2.0
    max_staleness_days: int = 5
    cache_ttl_seconds: int = 900

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be positive")
        if self.timeout_seconds <= 0.0 or self.requests_per_second <= 0.0:
            raise ValueError("timeout and request rate must be positive")
        if self.base_backoff_seconds < 0.0 or self.max_backoff_seconds < 0.0:
            raise ValueError("backoff must be non-negative")
        if self.max_backoff_seconds < self.base_backoff_seconds:
            raise ValueError("maximum backoff must be at least base backoff")
        if self.max_staleness_days < 0 or self.cache_ttl_seconds < 0:
            raise ValueError("staleness and cache TTL must be non-negative")


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    bars: tuple[MarketBar, ...]
    provider_name: str


class ResilientMarketDataProvider(MarketDataProvider):
    """Retry, fallback, throttle, timeout, freshness, and exact-request cache layer."""

    def __init__(
        self,
        primary: MarketDataProvider,
        *,
        fallback: MarketDataProvider | None = None,
        policy: ProviderPolicy | None = None,
        primary_name: str | None = None,
        fallback_name: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.policy = policy or ProviderPolicy()
        self.primary_name = primary_name or type(primary).__name__
        self.fallback_name = fallback_name or (type(fallback).__name__ if fallback else None)
        self.name = (
            f"{self.primary_name}->{self.fallback_name}"
            if self.fallback_name
            else self.primary_name
        )
        self._sleep = sleep
        self._monotonic = monotonic
        self._cache: dict[tuple[str, date, date], _CacheEntry] = {}
        self._cache_lock = threading.Lock()
        self._rate_lock = threading.Lock()
        self._next_request_at = 0.0
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="market-data")
        self._last_provider: dict[str, str] = {}

    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        normalized_ticker = ticker.strip().upper()
        key = (normalized_ticker, start_date, end_date)
        cached = self._cache_get(key)
        if cached is not None:
            self._last_provider[normalized_ticker] = cached.provider_name
            return list(cached.bars)

        providers = [(self.primary_name, self.primary)]
        if self.fallback is not None and self.fallback_name is not None:
            providers.append((self.fallback_name, self.fallback))
        failures: list[str] = []
        for provider_name, provider in providers:
            try:
                bars = self._fetch_with_retry(
                    provider_name, provider, normalized_ticker, start_date, end_date
                )
                self._cache_put(key, bars, provider_name)
                self._last_provider[normalized_ticker] = provider_name
                return list(bars)
            except Exception as exc:
                failures.append(f"{provider_name}: {type(exc).__name__}")
                logger.warning(
                    "market_data_provider_exhausted",
                    extra={
                        "ticker": normalized_ticker,
                        "provider": provider_name,
                        "error_type": type(exc).__name__,
                    },
                )
        raise MarketDataOperationalError(
            f"market data unavailable for {normalized_ticker}; {'; '.join(failures)}"
        )

    def last_provider_for(self, ticker: str) -> str | None:
        return self._last_provider.get(ticker.strip().upper())

    def cache_stats(self) -> dict[str, int]:
        with self._cache_lock:
            now = self._monotonic()
            active = sum(entry.expires_at >= now for entry in self._cache.values())
            return {"entries": len(self._cache), "active_entries": active}

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _fetch_with_retry(
        self,
        provider_name: str,
        provider: MarketDataProvider,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> tuple[MarketBar, ...]:
        last_error: Exception | None = None
        for attempt in range(1, self.policy.attempts + 1):
            self._throttle()
            try:
                future = self._executor.submit(provider.get_history, ticker, start_date, end_date)
                try:
                    received = future.result(timeout=self.policy.timeout_seconds)
                except FutureTimeoutError as exc:
                    future.cancel()
                    raise MarketDataTimeoutError(
                        f"{provider_name} exceeded {self.policy.timeout_seconds}s"
                    ) from exc
                bars = tuple(
                    sorted(
                        (
                            bar
                            for bar in received
                            if bar.ticker.upper() == ticker
                            and start_date <= bar.timestamp <= end_date
                        ),
                        key=lambda item: item.timestamp,
                    )
                )
                self._validate_freshness(ticker, bars, end_date)
                logger.info(
                    "market_data_fetch_succeeded",
                    extra={
                        "ticker": ticker,
                        "provider": provider_name,
                        "attempt": attempt,
                        "observation_count": len(bars),
                    },
                )
                return bars
            except Exception as exc:
                last_error = self._classify_error(exc)
                if attempt == self.policy.attempts:
                    break
                exponential_delay = self.policy.base_backoff_seconds * (2 ** (attempt - 1))
                retry_after = self._retry_after_seconds(exc)
                delay = min(
                    self.policy.max_backoff_seconds,
                    max(exponential_delay, retry_after),
                )
                logger.warning(
                    "market_data_fetch_retry",
                    extra={
                        "ticker": ticker,
                        "provider": provider_name,
                        "attempt": attempt,
                        "retry_delay_seconds": delay,
                        "error_type": type(last_error).__name__,
                    },
                )
                self._sleep(delay)
        assert last_error is not None
        raise last_error

    def _validate_freshness(self, ticker: str, bars: tuple[MarketBar, ...], end_date: date) -> None:
        if not bars:
            raise StaleMarketDataError(f"no market data returned for {ticker}")
        expected_through = end_date - timedelta(days=1)
        age = (expected_through - bars[-1].timestamp).days
        if age > self.policy.max_staleness_days:
            raise StaleMarketDataError(
                f"latest {ticker} bar is {age} days stale for {expected_through}"
            )

    @staticmethod
    def _classify_error(exc: Exception) -> Exception:
        if isinstance(exc, MarketDataOperationalError):
            return exc
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        message = str(exc).lower()
        if status == 429 or "rate limit" in message or "too many requests" in message:
            return MarketDataRateLimitError(str(exc))
        return MarketDataOperationalError(str(exc))

    @staticmethod
    def _retry_after_seconds(exc: Exception) -> float:
        value = getattr(exc, "retry_after", None)
        direct_headers = getattr(exc, "headers", {})
        if value is None and direct_headers:
            value = direct_headers.get("Retry-After")
        if value is None:
            response = getattr(exc, "response", None)
            headers = getattr(response, "headers", {}) if response is not None else {}
            value = headers.get("Retry-After") if headers else None
        try:
            return max(0.0, float(value)) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    def _throttle(self) -> None:
        interval = 1.0 / self.policy.requests_per_second
        with self._rate_lock:
            now = self._monotonic()
            wait = max(0.0, self._next_request_at - now)
            self._next_request_at = max(now, self._next_request_at) + interval
        if wait:
            self._sleep(wait)

    def _cache_get(self, key: tuple[str, date, date]) -> _CacheEntry | None:
        if self.policy.cache_ttl_seconds == 0:
            return None
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at < self._monotonic():
                del self._cache[key]
                return None
            return entry

    def _cache_put(
        self,
        key: tuple[str, date, date],
        bars: tuple[MarketBar, ...],
        provider_name: str,
    ) -> None:
        if self.policy.cache_ttl_seconds == 0:
            return
        with self._cache_lock:
            self._cache[key] = _CacheEntry(
                expires_at=self._monotonic() + self.policy.cache_ttl_seconds,
                bars=bars,
                provider_name=provider_name,
            )
