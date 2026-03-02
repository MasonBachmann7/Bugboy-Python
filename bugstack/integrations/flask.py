"""BugStack integration for Flask."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("bugstack")


def init_app(app: Any) -> None:
    """Register BugStack error handler on a Flask app.

    Usage:
        from flask import Flask
        import bugstack
        from bugstack.integrations.flask import init_app

        bugstack.init(api_key="bs_live_...")
        app = Flask(__name__)
        init_app(app)

    Captures unhandled exceptions and re-raises them so
    Flask's own error handling still works.
    """

    @app.errorhandler(Exception)
    def _bugstack_error_handler(exc: Exception) -> Any:
        try:
            import bugstack
            from flask import request as flask_request
            from ..types import RequestContext

            client = bugstack.get_client()
            if client:
                request_ctx = RequestContext(
                    route=flask_request.url_rule.rule if flask_request.url_rule else flask_request.path,
                    method=flask_request.method,
                )
                client.capture_exception(
                    exc,
                    request=request_ctx,
                    metadata={"framework": "flask"},
                )
        except Exception as inner:
            logger.warning("[BugStack] Error capturing exception: %s", inner)

        # Re-raise so Flask handles it normally
        raise exc

    # Also try to detect Flask version for environment info
    try:
        from importlib.metadata import version
        flask_version = version("flask")
        logger.debug("[BugStack] Flask integration initialized (Flask %s)", flask_version)
    except Exception:
        logger.debug("[BugStack] Flask integration initialized")
