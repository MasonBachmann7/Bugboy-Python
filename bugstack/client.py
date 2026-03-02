"""Core BugStack client."""

from __future__ import annotations

import logging
import sys
import re
from datetime import datetime, timezone
from typing import Any, Optional, Union

from .fingerprint import (
    Deduplicator,
    extract_error_location,
    format_traceback,
    generate_fingerprint,
)
from .transport import Transport
from .types import BugStackConfig, ErrorEvent, EnvironmentInfo, RequestContext

logger = logging.getLogger("bugstack")


class BugStackClient:
    """Core client for capturing and reporting errors to BugStack.

    Thread-safe. Handles deduplication, filtering, and transport.
    """

    def __init__(self, config: BugStackConfig) -> None:
        self._config = config
        self._deduplicator = Deduplicator(window=config.deduplication_window)
        self._transport: Optional[Transport] = None

        if config.enabled and not config.dry_run:
            self._transport = Transport(
                endpoint=config.endpoint,
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries,
                debug=config.debug,
            )

        if config.debug:
            # Attach a handler directly to the bugstack logger so debug
            # output is visible even when a WSGI server (e.g. Gunicorn)
            # has already configured the root logger (making basicConfig a no-op).
            if not logger.handlers:
                handler = logging.StreamHandler(sys.stderr)
                handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
                logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            logger.debug(
                "[BugStack] Client initialized (endpoint=%s, dry_run=%s)",
                config.endpoint,
                config.dry_run,
            )

    @property
    def config(self) -> BugStackConfig:
        return self._config

    def capture_exception(
        self,
        exc: BaseException,
        request: Optional[RequestContext] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Capture an exception and send it to BugStack.

        Returns True if the error was accepted (not filtered/deduplicated).
        Never raises — all errors are caught and logged in debug mode.
        """
        try:
            return self._do_capture(exc, request, metadata)
        except Exception as inner:
            if self._config.debug:
                logger.error("[BugStack] Error during capture: %s", inner)
            return False

    def _do_capture(
        self,
        exc: BaseException,
        request: Optional[RequestContext],
        metadata: Optional[dict[str, Any]],
    ) -> bool:
        if not self._config.enabled:
            return False

        # Check ignored_errors
        if self._is_ignored(exc):
            if self._config.debug:
                logger.debug("[BugStack] Error ignored: %s", type(exc).__name__)
            return False

        # Extract location info
        exc_type, file, function, line = extract_error_location(exc)
        stack_trace = format_traceback(exc)

        # Build event
        event = ErrorEvent(
            message=str(exc),
            stack_trace=stack_trace,
            file=file,
            function=function,
            exception_type=exc_type,
            fingerprint=generate_fingerprint(exc_type, file, function, line),
            request=request,
            environment=EnvironmentInfo(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )

        # before_send hook
        if self._config.before_send:
            result = self._config.before_send(event)
            if result is None:
                if self._config.debug:
                    logger.debug("[BugStack] Event dropped by before_send")
                return False
            event = result

        # Deduplication
        if not self._deduplicator.should_send(event.fingerprint):
            if self._config.debug:
                logger.debug("[BugStack] Event deduplicated: %s", event.fingerprint)
            return False

        # Build payload
        payload = event.to_payload(self._config)

        # Dry run mode
        if self._config.dry_run:
            import json
            print(f"[BugStack DryRun] Would send: {json.dumps(payload, indent=2)}")
            return True

        # Enqueue for sending
        if self._transport:
            self._transport.enqueue(payload)

        if self._config.debug:
            logger.debug("[BugStack] Event queued: %s", event.fingerprint)

        return True

    def _is_ignored(self, exc: BaseException) -> bool:
        """Check if an exception matches any ignored_errors patterns."""
        for pattern in self._config.ignored_errors:
            if isinstance(pattern, type) and isinstance(exc, pattern):
                return True
            if isinstance(pattern, str) and pattern == str(exc):
                return True
        return False

    def shutdown(self) -> None:
        """Shut down the client and flush pending events."""
        if self._transport:
            self._transport.shutdown()
