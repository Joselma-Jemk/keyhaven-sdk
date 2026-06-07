"""Tests for `Keyhaven.health()` / `Keyhaven.health_sync()`."""

from __future__ import annotations

import httpx
import pytest
import respx

from keyhaven.sdk import Keyhaven
from keyhaven.sdk.exceptions import KeyhavenHTTPError

BASE_URL = "http://test.invalid"


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_body_on_200(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/v1/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
            async with Keyhaven(BASE_URL, "k") as client:
                result = await client.health()
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_returns_empty_dict_on_204(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/v1/health").mock(return_value=httpx.Response(204))
            async with Keyhaven(BASE_URL, "k") as client:
                result = await client.health()
        assert result == {}

    @pytest.mark.asyncio
    async def test_health_raises_on_500(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/v1/health").mock(
                return_value=httpx.Response(
                    500, json={"error": {"code": "INTERNAL", "message": "boom"}}
                )
            )
            async with Keyhaven(BASE_URL, "k") as client:
                with pytest.raises(KeyhavenHTTPError) as exc:
                    await client.health()
        assert exc.value.status_code == 500

    def test_health_sync_wrapper(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/v1/health").mock(
                return_value=httpx.Response(200, json={"status": "ok", "version": "1.0"})
            )
            client = Keyhaven(BASE_URL, "k")
            result = client.health_sync()
        assert result == {"status": "ok", "version": "1.0"}
