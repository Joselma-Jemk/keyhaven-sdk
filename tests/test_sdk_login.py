from __future__ import annotations

import httpx
import pytest
import respx

from keyhaven.sdk import Keyhaven
from keyhaven.sdk.exceptions import KeyhavenHTTPError

BASE_URL = "https://keyhaven.example.com"
API_KEY = "prx_test_key_abc123"


def _error_json(code: str, message: str, status: int) -> httpx.Response:
    return httpx.Response(
        status,
        json={"success": False, "error": {"code": code, "message": message}},
    )


class TestLoginStart:
    @pytest.mark.asyncio
    async def test_login_start_returns_auth_url(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.post(f"{BASE_URL}/v1/login/start").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "auth_url": "https://accounts.google.com/o/oauth2/auth?state=xyz",
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                url = await p.login_start("google", "https://app.example.com/cb")

        import json

        body = json.loads(route.calls.last.request.content)
        assert body == {"provider": "google", "redirect_uri": "https://app.example.com/cb"}
        assert url == "https://accounts.google.com/o/oauth2/auth?state=xyz"

    @pytest.mark.asyncio
    async def test_login_start_raises_on_400(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/login/start").mock(
                return_value=_error_json("INVALID_PROVIDER", "unknown provider", 400)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(KeyhavenHTTPError) as exc:
                    await p.login_start("unknown", "https://app/cb")
        assert exc.value.status_code == 400
        assert exc.value.error_code == "INVALID_PROVIDER"


class TestLoginExchange:
    @pytest.mark.asyncio
    async def test_login_exchange_returns_claims(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/login/exchange").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "claims": {
                            "provider": "google",
                            "email": "user@gmail.com",
                            "sub": "google_12345",
                            "name": "Alice",
                            "picture": "https://example.com/avatar.png",
                            "email_verified": True,
                        },
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                claims = await p.login_exchange("tok_abc123")

        assert claims["provider"] == "google"
        assert claims["email"] == "user@gmail.com"
        assert claims["sub"] == "google_12345"

    @pytest.mark.asyncio
    async def test_login_exchange_raises_on_400(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/login/exchange").mock(
                return_value=_error_json("TOKEN_EXPIRED", "login token has expired", 400)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(KeyhavenHTTPError) as exc:
                    await p.login_exchange("tok_expired")
        assert exc.value.status_code == 400
        assert exc.value.error_code == "TOKEN_EXPIRED"


class TestSyncWrappers:
    def test_login_start_sync_wrapper(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/login/start").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "auth_url": "https://accounts.google.com/o/oauth2/auth?state=xyz",
                    },
                )
            )
            p = Keyhaven(BASE_URL, API_KEY)
            url = p.login_start_sync("google", "https://app/cb")
        assert url == "https://accounts.google.com/o/oauth2/auth?state=xyz"
