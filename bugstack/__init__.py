"""BugStack SDK — Production error capture for BugStack.

Usage:
    import bugstack

    bugstack.init(api_key="bs_live_...")

    # Errors are captured automatically via framework integrations.
    # For manual capture:
    try:
        risky_operation()
    except Exception as e:
        bugstack.capture_exception(e)
"""

from __future__ import annotations

import atexit
from typing import Any, Optional

from .client import BugStackClient
from .types import BugStackConfig, ErrorEvent, RequestContext, SDK_VERSION

__version__ = SDK_VERSION
__all__ = [
    "init",
    "capture_exception",
    "get_client",
    "BugStackConfig",
    "ErrorEvent",
    "RequestContext",
]

_client: Optional[BugStackClient] = None


def init(
    api_key: str,
    *,
    endpoint: str = "https://api.bugstack.dev/api/capture",
    project_id: str = "",
    environment: str = "production",
    auto_fix: bool = False,
    enabled: bool = True,
    debug: bool = False,
    dry_run: bool = False,
    deduplication_window: float = 300.0,
    timeout: float = 5.0,
    max_retries: int = 3,
    ignored_errors: Optional[list] = None,
    before_send: Optional[Any] = None,
    redact_fields: Optional[list[str]] = None,
) -> BugStackClient:
    """Initialize the BugStack SDK.

    Call this once at application startup.

    Args:
        api_key: Your BugStack API key (required).
        endpoint: BugStack API endpoint.
        project_id: Project identifier.
        environment: Environment name (e.g., "production").
        auto_fix: Enable autonomous error fixing.
        enabled: Kill switch — set to False to disable everything.
        debug: Log SDK activity to console.
        dry_run: Log errors but don't send them.
        deduplication_window: Dedup window in seconds (default: 300).
        timeout: HTTP timeout in seconds (default: 5).
        max_retries: Max retry attempts (default: 3).
        ignored_errors: Error types or messages to ignore.
        before_send: Hook to inspect/modify/drop events.
        redact_fields: Additional field names to redact.

    Returns:
        The initialized BugStackClient.
    """
    global _client

    if _client is not None:
        _client.shutdown()

    config = BugStackConfig(
        api_key=api_key,
        endpoint=endpoint,
        project_id=project_id,
        environment=environment,
        auto_fix=auto_fix,
        enabled=enabled,
        debug=debug,
        dry_run=dry_run,
        deduplication_window=deduplication_window,
        timeout=timeout,
        max_retries=max_retries,
        ignored_errors=ignored_errors or [],
        before_send=before_send,
        redact_fields=redact_fields or [],
    )

    _client = BugStackClient(config)

    atexit.register(_shutdown)

    return _client


def capture_exception(
    exc: Optional[BaseException] = None,
    *,
    request: Optional[RequestContext] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """Capture an exception and send it to BugStack.

    If no exception is passed, captures the current exception from sys.exc_info().

    Returns True if the error was accepted.
    """
    if _client is None:
        import warnings
        warnings.warn("BugStack not initialized. Call bugstack.init() first.", stacklevel=2)
        return False

    if exc is None:
        import sys
        _, exc_val, _ = sys.exc_info()
        if exc_val is None:
            return False
        exc = exc_val

    return _client.capture_exception(exc, request=request, metadata=metadata)


def get_client() -> Optional[BugStackClient]:
    """Get the current BugStack client instance."""
    return _client


def _shutdown() -> None:
    global _client
    if _client is not None:
        _client.shutdown()
        _client = None
