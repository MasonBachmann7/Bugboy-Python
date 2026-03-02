"""Type definitions for the BugStack SDK."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

SDK_VERSION = "1.1.0"


@dataclass
class BugStackConfig:
    """Configuration for the BugStack SDK."""

    api_key: str
    endpoint: str = "https://api.bugstack.dev/api/capture"
    project_id: str = ""
    environment: str = "production"
    auto_fix: bool = False
    enabled: bool = True
    debug: bool = False
    dry_run: bool = False
    deduplication_window: float = 300.0  # 5 minutes
    timeout: float = 5.0  # seconds
    max_retries: int = 3
    ignored_errors: list[Union[str, type]] = field(default_factory=list)
    before_send: Optional[Callable[["ErrorEvent"], Optional["ErrorEvent"]]] = None
    redact_fields: list[str] = field(default_factory=list)


@dataclass
class RequestContext:
    """HTTP request context attached to an error event."""

    route: str = ""
    method: str = ""
    query_params: Optional[dict[str, str]] = None
    headers: Optional[dict[str, str]] = None
    body: Optional[Any] = None


@dataclass
class EnvironmentInfo:
    """Runtime environment information."""

    language: str = "python"
    language_version: str = field(default_factory=lambda: platform.python_version())
    framework: str = ""
    framework_version: str = ""
    os: str = field(default_factory=lambda: sys.platform)
    sdk_version: str = SDK_VERSION


@dataclass
class ErrorEvent:
    """An error event to be sent to BugStack."""

    message: str
    stack_trace: str = ""
    file: str = ""
    function: str = ""
    fingerprint: str = ""
    exception_type: str = ""
    request: Optional[RequestContext] = None
    environment: EnvironmentInfo = field(default_factory=EnvironmentInfo)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self, config: BugStackConfig) -> dict[str, Any]:
        """Serialize to the standard BugStack API payload."""
        payload: dict[str, Any] = {
            "apiKey": config.api_key,
            "error": {
                "message": self.message,
                "stackTrace": self.stack_trace,
                "file": self.file,
                "function": self.function,
                "fingerprint": self.fingerprint,
            },
            "environment": {
                "language": self.environment.language,
                "languageVersion": self.environment.language_version,
                "framework": self.environment.framework,
                "frameworkVersion": self.environment.framework_version,
                "os": self.environment.os,
                "sdkVersion": self.environment.sdk_version,
            },
            "timestamp": self.timestamp,
        }

        if self.request:
            payload["request"] = {
                "route": self.request.route,
                "method": self.request.method,
            }

        if config.project_id:
            payload["projectId"] = config.project_id

        if self.metadata:
            payload["metadata"] = self.metadata

        if config.auto_fix:
            payload.setdefault("metadata", {})["autoFix"] = True

        return payload
