from __future__ import annotations

from typing import Any


class KeyhavenError(Exception):
    """Base for all Keyhaven SDK errors."""


class KeyhavenHTTPError(KeyhavenError):
    """Wraps a non-2xx HTTP response from the Keyhaven server."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class AuthenticationError(KeyhavenHTTPError):
    """401 — missing/invalid/revoked API key."""


class OwnerMismatchError(KeyhavenHTTPError):
    """403 — API key not authorized for the requested owner."""


class NotFoundError(KeyhavenHTTPError):
    """404 — function or linked account does not exist."""


class ProviderError(KeyhavenHTTPError):
    """502 — the downstream provider (Gmail, Slack…) failed."""


class ValidationError(KeyhavenHTTPError):
    """422 — request body / args failed schema validation."""


class ConflictError(KeyhavenHTTPError):
    """409 — request conflicts with current state (e.g. duplicate)."""


class RateLimitError(KeyhavenHTTPError):
    """429 — too many requests. Inspect `retry_after_seconds` (from Retry-After header)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, error_code=error_code, details=details)
        self.retry_after_seconds = retry_after_seconds


class KeyhavenTimeoutError(KeyhavenError):
    """The request to Keyhaven exceeded the configured timeout."""


class KeyhavenNetworkError(KeyhavenError):
    """Network failure reaching the Keyhaven server (wraps httpx.RequestError)."""
