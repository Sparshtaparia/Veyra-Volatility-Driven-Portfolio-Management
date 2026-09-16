"""Vendor-neutral error-monitoring hooks."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger("veyra.errors")
ErrorReporter = Callable[[Exception, dict[str, object]], None]


class ErrorMonitor:
    def __init__(self) -> None:
        self._reporters: list[ErrorReporter] = []
        self._lock = threading.Lock()

    def register(self, reporter: ErrorReporter) -> None:
        with self._lock:
            self._reporters.append(reporter)

    def capture(self, error: Exception, context: dict[str, object]) -> None:
        logger.error(
            "application_error",
            exc_info=error,
            extra={**context, "error_type": type(error).__name__},
        )
        with self._lock:
            reporters = list(self._reporters)
        for reporter in reporters:
            try:
                reporter(error, context)
            except Exception:
                logger.exception("error_reporter_failed")


error_monitor = ErrorMonitor()
