"""BugStack generic Python integration.

Hooks sys.excepthook and threading.excepthook to capture
all unhandled exceptions.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import Any, Optional

logger = logging.getLogger("bugstack")

_original_excepthook = sys.excepthook
_original_threading_excepthook = getattr(threading, "excepthook", None)


def install_hooks() -> None:
    """Install global exception hooks.

    Usage:
        import bugstack
        from bugstack.integrations.generic import install_hooks

        bugstack.init(api_key="bs_live_...")
        install_hooks()
    """
    sys.excepthook = _bugstack_excepthook

    if hasattr(threading, "excepthook"):
        threading.excepthook = _bugstack_threading_excepthook

    logger.debug("[BugStack] Global exception hooks installed")


def uninstall_hooks() -> None:
    """Restore original exception hooks."""
    sys.excepthook = _original_excepthook

    if _original_threading_excepthook is not None:
        threading.excepthook = _original_threading_excepthook


def _bugstack_excepthook(exc_type: type, exc_value: BaseException, exc_tb: Any) -> None:
    """Custom sys.excepthook that captures exceptions before passing through."""
    try:
        import bugstack
        bugstack.capture_exception(exc_value)
    except Exception:
        pass

    # Call the original hook so normal behavior (printing traceback) still happens
    _original_excepthook(exc_type, exc_value, exc_tb)


def _bugstack_threading_excepthook(args: Any) -> None:
    """Custom threading.excepthook for unhandled thread exceptions."""
    try:
        import bugstack
        if args.exc_value is not None:
            bugstack.capture_exception(
                args.exc_value,
                metadata={"thread": args.thread.name if args.thread else "unknown"},
            )
    except Exception:
        pass

    if _original_threading_excepthook is not None:
        _original_threading_excepthook(args)
