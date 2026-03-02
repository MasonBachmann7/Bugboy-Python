"""Error fingerprinting and client-side deduplication."""

from __future__ import annotations

import hashlib
import time
import traceback
import threading
from typing import Optional


def generate_fingerprint(
    exception_type: str,
    file: str,
    function: str,
    line: Optional[int] = None,
) -> str:
    """Generate a stable SHA-256 fingerprint for an error.

    Based on exception type, file, function, and line number.
    The same error at the same location always produces the same hash.
    """
    parts = [exception_type, file, function]
    if line is not None:
        parts.append(str(line))
    key = ":".join(parts)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def extract_error_location(
    exc: BaseException,
) -> tuple[str, str, str, Optional[int]]:
    """Extract file, function, line from an exception's traceback.

    Returns (exception_type, file, function, line).
    """
    exception_type = type(exc).__name__

    tb = exc.__traceback__
    if tb is None:
        return exception_type, "", "", None

    # Walk to the last (innermost) frame
    while tb.tb_next is not None:
        tb = tb.tb_next

    frame = tb.tb_frame
    file = frame.f_code.co_filename
    function = frame.f_code.co_name
    line = tb.tb_lineno

    return exception_type, file, function, line


def format_traceback(exc: BaseException) -> str:
    """Format an exception's traceback as a string."""
    lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return "".join(lines)


class Deduplicator:
    """Client-side error deduplicator.

    Prevents the same error (by fingerprint) from being reported
    more than once within a configurable time window.
    """

    def __init__(self, window: float = 300.0) -> None:
        self._cache: dict[str, float] = {}
        self._window = window
        self._lock = threading.Lock()

    def should_send(self, fingerprint: str) -> bool:
        """Check if an error should be sent. Thread-safe."""
        now = time.monotonic()

        with self._lock:
            last_sent = self._cache.get(fingerprint)
            if last_sent is not None and (now - last_sent) < self._window:
                return False
            self._cache[fingerprint] = now
            self._cleanup(now)
            return True

    def _cleanup(self, now: float) -> None:
        """Remove expired entries."""
        expired = [
            fp for fp, ts in self._cache.items()
            if (now - ts) >= self._window
        ]
        for fp in expired:
            del self._cache[fp]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
