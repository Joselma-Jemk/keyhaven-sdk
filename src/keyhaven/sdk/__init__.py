"""Keyhaven Python SDK — async-first HTTP client + optional LangChain integration.

Quick start
-----------

    from keyhaven.sdk import Keyhaven, RetryConfig

    async with Keyhaven(
        base_url="https://keyhaven.example.com",
        api_key="prx_live_...",
        retry=RetryConfig(max_attempts=3),
    ) as client:

        # 1. OAuth — get the URL to redirect the user to
        auth_url = await client.connect("gmail", owner_id="user_42")

        # 2. Execute a function (after the user has consented)
        result = await client.app("gmail").send_email(
            owner_id="user_42",
            to="boss@example.com",
            subject="Status",
            body="All green.",
        )

        # 3. House-keeping
        accounts = await client.list_linked_accounts("user_42")
        await client.disconnect("gmail", owner_id="user_42")

Every async method has a ``_sync`` sibling (``connect_sync``, ``execute_sync``,
``list_apps_sync``, ``list_linked_accounts_sync``, ``disconnect_sync``,
``health_sync``).

Exception hierarchy
-------------------

::

    KeyhavenError
    ├── KeyhavenNetworkError       # DNS / conn refused / etc.
    ├── KeyhavenTimeoutError       # request exceeded timeout
    └── KeyhavenHTTPError          # any non-2xx response
        ├── AuthenticationError  # 401
        ├── OwnerMismatchError   # 403
        ├── NotFoundError        # 404
        ├── ConflictError        # 409
        ├── ValidationError      # 422
        ├── RateLimitError       # 429 — see .retry_after_seconds
        └── ProviderError        # 502 — downstream API failed

See ``docs/sdk.md`` and ``examples/`` for full examples.
"""

from keyhaven.sdk._constants import DEFAULT_ACCOUNT_ID
from keyhaven.sdk.app_handle import AppHandle
from keyhaven.sdk.apps import Apps
from keyhaven.sdk.client import Keyhaven
from keyhaven.sdk.exceptions import (
    AuthenticationError,
    ConflictError,
    KeyhavenError,
    KeyhavenHTTPError,
    KeyhavenNetworkError,
    KeyhavenTimeoutError,
    NotFoundError,
    OwnerMismatchError,
    ProviderError,
    RateLimitError,
    ValidationError,
)
from keyhaven.sdk.retry import DISABLED, RetryConfig

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
]
