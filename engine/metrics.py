"""
Lightweight metrics collector for observability.
Emits structured metric events. Plug into Prometheus, Datadog, or CloudWatch.
"""
import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    name: str
    value: float
    unit: str = "count"
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    def __init__(self, prefix: str = "crm_ai", enabled: bool = True):
        self._prefix = prefix
        self._enabled = enabled
        self._buffer: list[Metric] = []

    def emit(self, name: str, value: float, unit: str = "count",
             tags: Optional[dict[str, str]] = None) -> None:
        if not self._enabled:
            return
        metric = Metric(
            name=f"{self._prefix}.{name}",
            value=value,
            unit=unit,
            tags=tags or {},
        )
        self._buffer.append(metric)
        logger.debug("metric: %s=%s %s %s", metric.name, metric.value, metric.unit, metric.tags)

    def increment(self, name: str, tags: Optional[dict[str, str]] = None) -> None:
        self.emit(name, 1.0, "count", tags)

    def gauge(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        self.emit(name, value, "gauge", tags)

    @contextmanager
    def timer(self, name: str, tags: Optional[dict[str, str]] = None):
        start = time.monotonic()
        try:
            yield
        finally:
            elapsed = time.monotonic() - start
            self.emit(name, elapsed, "seconds", tags)

    def flush(self) -> list[Metric]:
        batch = self._buffer.copy()
        self._buffer.clear()
        return batch
