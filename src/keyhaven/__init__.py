"""Keyhaven — open-source Python client SDK for the Keyhaven service.

OAuth and tool-calling for AI agents. This package is the MIT-licensed client;
the Keyhaven server is a separate, proprietary component.

The public API is re-exported here so both ``from keyhaven import Keyhaven`` and
``from keyhaven.sdk import Keyhaven`` work.
"""

from __future__ import annotations

from keyhaven.sdk import (
    DEFAULT_ACCOUNT_ID,
    DISABLED,
    AppHandle,
    Apps,
    AuthenticationError,
    ConflictError,
    Keyhaven,
    KeyhavenError,
    KeyhavenHTTPError,
    KeyhavenNetworkError,
    KeyhavenTimeoutError,
    NotFoundError,
    OwnerMismatchError,
    ProviderError,
    RateLimitError,
    RetryConfig,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_ACCOUNT_ID",
    "DISABLED",
    "AppHandle",
    "Apps",
    "AuthenticationError",
    "ConflictError",
    "Keyhaven",
    "KeyhavenError",
    "KeyhavenHTTPError",
    "KeyhavenNetworkError",
    "KeyhavenTimeoutError",
    "NotFoundError",
    "OwnerMismatchError",
    "ProviderError",
    "RateLimitError",
    "RetryConfig",
    "ValidationError",
    "__version__",
]
