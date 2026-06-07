"""Tests for `keyhaven.sdk.retry`."""

from __future__ import annotations

import httpx
import pytest
import respx

from keyhaven.sdk import (
    DISABLED,
    Keyhaven,
    KeyhavenNetworkError,
    RateLimitError,
    RetryConfig,
    ValidationError,
)
from keyhaven.sdk.retry import with_retry


@pytest.fixture
def fast_retry() -> RetryConfig:
    """A retry policy that runs all 3 attempts in ~zero time (no real sleep)."""
    return RetryConfig(
        max_attempts=3,
        backoff_initial=0.0,
        backoff_factor=1.0,
        backoff_max=0.0,
        jitter=False,
    )


def test_disabled_means_one_attempt() -> None:
    assert DISABLED.max_attempts == 1
    assert DISABLED._delay(0) == 0


def test_backoff_growth() -> None:
    cfg = RetryConfig(
        max_attempts=5,
        backoff_initial=1.0,
        backoff_factor=2.0,
        backoff_max=100.0,
        jitter=False,
    )
    assert cfg._delay(0) == 0
    assert cfg._delay(1) == 1.0
    assert cfg._delay(2) == 2.0
    assert cfg._delay(3) == 4.0
    assert cfg._delay(4) == 8.0


def test_backoff_capped_by_max() -> None:
    cfg = RetryConfig(
        max_attempts=5,
        backoff_initial=10.0,
        backoff_factor=10.0,
        backoff_max=15.0,
        jitter=False,
    )
    assert cfg._delay(2) == 15.0  # would be 100 without cap
    assert cfg._delay(3) == 15.0


@pytest.mark.asyncio
async def test_with_retry_succeeds_first_try(fast_retry: RetryConfig) -> None:
    calls = 0

    async def good() -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    response = await with_retry(good, fast_retry)
    assert response.status_code == 200
    assert calls == 1


@pytest.mark.asyncio
async def test_with_retry_retries_on_503(fast_retry: RetryConfig) -> None:
    calls = 0

    async def flaky() -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(200)

    response = await with_retry(flaky, fast_retry)
    assert response.status_code == 200
    assert calls == 3


@pytest.mark.asyncio
async def test_with_retry_gives_up_after_max_attempts(fast_retry: RetryConfig) -> None:
    calls = 0

    async def always_503() -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    response = await with_retry(always_503, fast_retry)
    # On the final attempt we return whatever the response was.
    assert response.status_code == 503
    assert calls == fast_retry.max_attempts


@pytest.mark.asyncio
async def test_with_retry_retries_on_network_error(fast_retry: RetryConfig) -> None:
    calls = 0

    async def flaky() -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise httpx.ConnectError("boom")
        return httpx.Response(200)

    response = await with_retry(flaky, fast_retry)
    assert response.status_code == 200
    assert calls == 2


@pytest.mark.asyncio
async def test_with_retry_raises_after_repeated_network_errors(
    fast_retry: RetryConfig,
) -> None:
    async def always_fail() -> httpx.Response:
        raise httpx.ConnectError("never works")

    with pytest.raises(httpx.ConnectError):
        await with_retry(always_fail, fast_retry)


@pytest.mark.asyncio
async def test_client_retries_5xx_then_succeeds(fast_retry: RetryConfig) -> None:
    with respx.mock(base_url="http://test.invalid") as router:
        route = router.get("/v1/apps").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json={"apps": [{"name": "gmail"}]}),
            ]
        )
        async with Keyhaven("http://test.invalid", api_key="k", retry=fast_retry) as client:
            apps = await client.list_apps()
        assert route.call_count == 2
        assert apps == [{"name": "gmail"}]


@pytest.mark.asyncio
async def test_client_does_not_retry_400() -> None:
    with respx.mock(base_url="http://test.invalid") as router:
        route = router.post("/v1/execute").mock(
            return_value=httpx.Response(422, json={"error": {"code": "BAD", "message": "nope"}})
        )
        async with Keyhaven(
            "http://test.invalid",
            api_key="k",
            retry=RetryConfig(max_attempts=3, backoff_initial=0.0, jitter=False),
        ) as client:
            with pytest.raises(ValidationError):
                await client.execute("gmail.send_email", "u", {})
        assert route.call_count == 1  # no retry on 422


@pytest.mark.asyncio
async def test_client_raises_rate_limit_with_retry_after() -> None:
    with respx.mock(base_url="http://test.invalid") as router:
        router.post("/v1/execute").mock(
            return_value=httpx.Response(
                429,
                json={"error": {"code": "RATE", "message": "slow down"}},
                headers={"Retry-After": "7.5"},
            )
        )
        async with Keyhaven(
            "http://test.invalid",
            api_key="k",
            retry=DISABLED,
        ) as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client.execute("gmail.send_email", "u", {})
            assert exc_info.value.retry_after_seconds == 7.5


@pytest.mark.asyncio
async def test_client_wraps_network_error_as_keyhaven_network_error() -> None:
    with respx.mock(base_url="http://test.invalid") as router:
        router.get("/v1/apps").mock(side_effect=httpx.ConnectError("dead"))
        async with Keyhaven(
            "http://test.invalid",
            api_key="k",
            retry=DISABLED,
        ) as client:
            with pytest.raises(KeyhavenNetworkError):
                await client.list_apps()
