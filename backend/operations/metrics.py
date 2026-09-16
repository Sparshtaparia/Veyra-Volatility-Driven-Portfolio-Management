"""Process-local lightweight counters and duration summaries."""

from __future__ import annotations

import threading
from collections import defaultdict


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._timings: dict[str, dict[str, float | int]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe_ms(self, name: str, duration_ms: float) -> None:
        with self._lock:
            values = self._timings.setdefault(name, {"count": 0, "total_ms": 0.0, "max_ms": 0.0})
            values["count"] = int(values["count"]) + 1
            values["total_ms"] = float(values["total_ms"]) + duration_ms
            values["max_ms"] = max(float(values["max_ms"]), duration_ms)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            timings = {
                name: {
                    **values,
                    "average_ms": (
                        float(values["total_ms"]) / int(values["count"])
                        if int(values["count"])
                        else 0.0
                    ),
                }
                for name, values in self._timings.items()
            }
            return {"counters": dict(self._counters), "timings": timings}


metrics = MetricsRegistry()
