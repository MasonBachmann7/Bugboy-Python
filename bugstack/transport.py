"""HTTP transport with async support and retry logic."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Optional

from .types import SDK_VERSION

logger = logging.getLogger("bugstack")

# Lazy import httpx to give a clear error if not installed
_httpx = None


def _get_httpx():
    global _httpx
    if _httpx is None:
        try:
            import httpx
            _httpx = httpx
        except ImportError:
            raise ImportError(
                "bugstack requires httpx. Install it with: pip install httpx"
            )
    return _httpx


class Transport:
    """HTTP transport that sends error events to the BugStack API.

    Handles retry with exponential backoff and background sending.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout: float = 5.0,
        max_retries: int = 3,
        debug: bool = False,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._debug = debug
        self._worker_thread: Optional[threading.Thread] = None
        self._queue: list[dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._owner_pid = os.getpid()
        self._start_worker()

    def _start_worker(self) -> None:
        """Start background worker thread for sending events."""
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="bugstack-transport",
        )
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Process queued events in the background."""
        while not self._stop_event.is_set():
            try:
                payloads: list[dict[str, Any]] = []
                with self._queue_lock:
                    if self._queue:
                        payloads = self._queue[:]
                        self._queue.clear()

                for payload in payloads:
                    self._send_with_retry(payload)
            except Exception as exc:
                if self._debug:
                    logger.warning("[BugStack] Worker loop error: %s", exc)

            self._stop_event.wait(timeout=0.5)

    def _ensure_worker_alive(self) -> None:
        """Restart the worker thread if it died (e.g. after os.fork in Gunicorn)."""
        current_pid = os.getpid()
        if current_pid != self._owner_pid:
            # We're in a forked child — reset state and start fresh
            if self._debug:
                logger.debug("[BugStack] Fork detected (pid %d -> %d), restarting worker", self._owner_pid, current_pid)
            self._owner_pid = current_pid
            self._stop_event = threading.Event()
            self._queue_lock = threading.Lock()
            self._start_worker()
        elif self._worker_thread is None or not self._worker_thread.is_alive():
            if self._debug:
                logger.debug("[BugStack] Worker thread dead, restarting")
            self._stop_event.clear()
            self._start_worker()

    def enqueue(self, payload: dict[str, Any]) -> None:
        """Add a payload to the send queue (non-blocking)."""
        self._ensure_worker_alive()
        with self._queue_lock:
            # Bound the queue to prevent unbounded memory growth
            if len(self._queue) < 100:
                self._queue.append(payload)
            elif self._debug:
                logger.warning("[BugStack] Queue full, dropping event")

    def _send_with_retry(self, payload: dict[str, Any]) -> bool:
        """Send a payload with exponential backoff retry."""
        httpx = _get_httpx()

        headers = {
            "Content-Type": "application/json",
            "X-BugStack-API-Key": self._api_key,
            "X-BugStack-SDK-Version": SDK_VERSION,
        }

        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        self._endpoint,
                        content=json.dumps(payload),
                        headers=headers,
                    )

                if response.status_code < 400:
                    if self._debug:
                        logger.debug("[BugStack] Event sent successfully")
                    return True

                if self._debug:
                    logger.warning(
                        "[BugStack] HTTP %d: %s",
                        response.status_code,
                        response.text[:200],
                    )

            except Exception as exc:
                if self._debug:
                    logger.warning("[BugStack] Send failed (attempt %d): %s", attempt + 1, exc)

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self._max_retries - 1:
                delay = 2 ** attempt
                time.sleep(delay)

        if self._debug:
            logger.error("[BugStack] Max retries exceeded, dropping event")
        return False

    async def send_async(self, payload: dict[str, Any]) -> bool:
        """Send a payload asynchronously (for async frameworks)."""
        httpx = _get_httpx()

        headers = {
            "Content-Type": "application/json",
            "X-BugStack-API-Key": self._api_key,
            "X-BugStack-SDK-Version": SDK_VERSION,
        }

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        self._endpoint,
                        content=json.dumps(payload),
                        headers=headers,
                    )

                if response.status_code < 400:
                    if self._debug:
                        logger.debug("[BugStack] Event sent successfully (async)")
                    return True

            except Exception as exc:
                if self._debug:
                    logger.warning("[BugStack] Async send failed (attempt %d): %s", attempt + 1, exc)

            if attempt < self._max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        return False

    def shutdown(self) -> None:
        """Stop the worker thread."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
