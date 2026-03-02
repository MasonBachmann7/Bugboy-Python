"""BugStack integration for FastAPI."""

from __future__ import annotations

import logging
from typing import Any

from ..types import RequestContext

logger = logging.getLogger("bugstack")


class FastAPIMiddleware:
    """ASGI middleware that captures unhandled exceptions in FastAPI.

    Usage:
        from fastapi import FastAPI
        from bugstack.integrations.fastapi import FastAPIMiddleware

        app = FastAPI()
        app.add_middleware(FastAPIMiddleware)

    The middleware captures the error, builds request context,
    and re-raises so FastAPI's own error handling still works.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self._framework_version = self._get_version()

    @staticmethod
    def _get_version() -> str:
        try:
            import fastapi
            return fastapi.__version__
        except Exception:
            return ""

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            import bugstack

            client = bugstack.get_client()
            if client:
                request_ctx = self._build_request_context(scope)

                # Set framework info
                from ..types import EnvironmentInfo
                env = EnvironmentInfo(
                    framework="fastapi",
                    framework_version=self._framework_version,
                )

                client.capture_exception(
                    exc,
                    request=request_ctx,
                    metadata={"framework": "fastapi"},
                )

            raise

    @staticmethod
    def _build_request_context(scope: dict) -> RequestContext:
        """Extract request context from ASGI scope."""
        path = scope.get("path", "")
        method = scope.get("method", "")

        # Extract query params
        query_string = scope.get("query_string", b"")
        query_params = None
        if query_string:
            from urllib.parse import parse_qs
            parsed = parse_qs(query_string.decode("utf-8", errors="replace"))
            query_params = {k: v[0] if len(v) == 1 else ",".join(v) for k, v in parsed.items()}

        # Extract route from path params if available
        route = path
        path_params = scope.get("path_params", {})
        if path_params:
            # Reconstruct route pattern from path and params
            for key, value in path_params.items():
                route = route.replace(str(value), f"{{{key}}}")

        return RequestContext(
            route=route,
            method=method,
            query_params=query_params,
        )
