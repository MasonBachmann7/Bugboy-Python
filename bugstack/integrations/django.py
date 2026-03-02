"""BugStack integration for Django."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("bugstack")


class BugStackMiddleware:
    """Django middleware that captures unhandled exceptions.

    Usage in settings.py:
        MIDDLEWARE = [
            'bugstack.integrations.django.BugStackMiddleware',
            # ... other middleware
        ]

        BUGSTACK_API_KEY = "bs_live_..."
        BUGSTACK_AUTO_FIX = True

    The middleware auto-initializes from Django settings if
    bugstack.init() hasn't been called yet.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        self._ensure_initialized()

    @staticmethod
    def _ensure_initialized() -> None:
        """Initialize BugStack from Django settings if not already done."""
        import bugstack

        if bugstack.get_client() is not None:
            return

        try:
            from django.conf import settings

            api_key = getattr(settings, "BUGSTACK_API_KEY", "")
            if not api_key:
                return

            bugstack.init(
                api_key=api_key,
                auto_fix=getattr(settings, "BUGSTACK_AUTO_FIX", False),
                environment=getattr(settings, "BUGSTACK_ENVIRONMENT", "production"),
                debug=getattr(settings, "BUGSTACK_DEBUG", False),
                dry_run=getattr(settings, "BUGSTACK_DRY_RUN", False),
            )
        except Exception as exc:
            logger.warning("[BugStack] Failed to auto-initialize from Django settings: %s", exc)

    def __call__(self, request: Any) -> Any:
        return self.get_response(request)

    def process_exception(self, request: Any, exception: Exception) -> None:
        """Called by Django when a view raises an exception."""
        try:
            import bugstack
            from ..types import RequestContext

            client = bugstack.get_client()
            if client is None:
                return

            request_ctx = self._build_request_context(request)
            client.capture_exception(
                exception,
                request=request_ctx,
                metadata={"framework": "django"},
            )
        except Exception as exc:
            logger.warning("[BugStack] Error capturing exception: %s", exc)

    @staticmethod
    def _build_request_context(request: Any) -> "RequestContext":
        from ..types import RequestContext

        route = ""
        try:
            if hasattr(request, "resolver_match") and request.resolver_match:
                route = request.resolver_match.route
            else:
                route = request.path
        except Exception:
            route = getattr(request, "path", "")

        method = getattr(request, "method", "")

        return RequestContext(route=route, method=method)
