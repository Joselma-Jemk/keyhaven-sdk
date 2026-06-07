"""Retry policy for the Keyhaven SDK client.

Wraps async HTTP calls with exponential backoff. Configurable via `RetryConfig`
passed to the `Keyhaven` client constructor; defaults are sensible for most
agentic workloads (3 attempts, half-second initial backoff, doubling).

Retry triggers:
- An HTTP response with a status code in ``retry_on_status`` (default
  ``{429, 500, 502, 503, 504}``).
- A network failure (``httpx.RequestError``) when ``retry_on_network`` is True.

Non-retried errors (auth, 4xx other than 429, validation) bubble up immediately.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryConfig:
    """Exponential backoff configuration for SDK calls.

    Attributes
    ----------
    max_attempts
        Total attempts including the first. Set to ``1`` to disable retry.
    backoff_initial
        Seconds before the **second** attempt. The next backoff is
        ``backoff_initial * backoff_factor`` and so on.
    backoff_factor
        Geometric growth ratio between attempts.
    backoff_max
        Hard cap on a single backoff delay (seconds).
    jitter
        If True, multiplies each backoff by a uniform ``[0.5, 1.5)`` factor to
        avoid thundering herd when many clients retry in lockstep.
    retry_on_status
        HTTP status codes to retry on.
    retry_on_network
        Whether to retry on ``httpx.RequestError`` (DNS, connection refused…).
    """

    max_attempts: int = 3
    backoff_initial: float = 0.5
    backoff_factor: float = 2.0
    backoff_max: float = 30.0
    jitter: bool = True
    retry_on_status: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )
    retry_on_network: bool = True

    def _delay(self, attempt_index: int) -> float:
        """Backoff before attempt #(attempt_index+1). 0 for the first attempt."""
        if attempt_index <= 0:
            return 0.0
        raw = self.backoff_initial * (self.backoff_factor ** (attempt_index - 1))
        delay = min(raw, self.backoff_max)
        if self.jitter:
            delay *= 0.5 + random.random()
        return delay


DISABLED = RetryConfig(max_attempts=1)
"""Convenience: a no-op retry policy (one attempt, no backoff)."""


async def with_retry(
    request: Callable[[], Awaitable[httpx.Response]],
    config: RetryConfig,
) -> httpx.Response:
    """Execute ``request()`` with retry policy. Returns the final ``httpx.Response``.

    Raises ``httpx.RequestError`` if all attempts hit network errors.
    The caller is still responsible for inspecting the response status.
    """
    last_exc: Exception | None = None
    for attempt_index in range(config.max_attempts):
        delay = config._delay(attempt_index)
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            response = await request()
        except httpx.RequestError as exc:
            last_exc = exc
            if not config.retry_on_network or attempt_index == config.max_attempts - 1:
                raise
            log.warning(
                "Keyhaven SDK: network error on attempt %d/%d — retrying: %s",
                attempt_index + 1,
                config.max_attempts,
                exc,
            )
            continue

        if (
            response.status_code in config.retry_on_status
            and attempt_index < config.max_attempts - 1
        ):
            log.warning(
                "Keyhaven SDK: status %d on attempt %d/%d — retrying",
                response.status_code,
                attempt_index + 1,
                config.max_attempts,
            )
            continue
        return response

    # Unreachable: either we returned a response, or a RequestError raised in the
    # final attempt. The line below satisfies type checkers.
    assert last_exc is not None
    raise last_exc
