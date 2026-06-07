from __future__ import annotations

import json

import httpx
import pytest
import respx

from keyhaven.sdk import Keyhaven
from keyhaven.sdk.exceptions import KeyhavenHTTPError

BASE_URL = "https://keyhaven.example.com"
API_KEY = "prx_test_key_abc123"


class TestSetProviderCredentials:
    @pytest.mark.asyncio
    async def test_set_sends_put_with_body(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.put(f"{BASE_URL}/v1/provider-credentials").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "kind": "tool",
                        "provider": "google",
                        "client_id": "gid",
                        "created_at": "2026-06-06T00:00:00Z",
                        "updated_at": "2026-06-06T00:00:00Z",
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                result = await p.set_provider_credentials("google", "gid", "gsecret")

        body = json.loads(route.calls.last.request.content)
        assert body == {
            "kind": "tool",
            "provider": "google",
            "client_id": "gid",
            "client_secret": "gsecret",
        }
        assert result["provider"] == "google"
        assert "client_secret" not in result

    @pytest.mark.asyncio
    async def test_set_login_kind(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.put(f"{BASE_URL}/v1/provider-credentials").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "kind": "login",
                        "provider": "google",
                        "client_id": "lid",
                        "created_at": "2026-06-06T00:00:00Z",
                        "updated_at": "2026-06-06T00:00:00Z",
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.set_provider_credentials("google", "lid", "lsecret", kind="login")
        body = json.loads(route.calls.last.request.content)
        assert body["kind"] == "login"

    @pytest.mark.asyncio
    async def test_set_raises_on_403(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.put(f"{BASE_URL}/v1/provider-credentials").mock(
                return_value=httpx.Response(
                    403,
                    json={"success": False, "error": {"code": "FORBIDDEN", "message": "no"}},
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(KeyhavenHTTPError) as exc:
                    await p.set_provider_credentials("google", "i", "s")
        assert exc.value.status_code == 403


class TestListAndDelete:
    @pytest.mark.asyncio
    async def test_list_returns_items(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/provider-credentials").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "provider_credentials": [
                            {
                                "kind": "tool",
                                "provider": "google",
                                "client_id": "gid",
                                "created_at": "2026-06-06T00:00:00Z",
                                "updated_at": "2026-06-06T00:00:00Z",
                            }
                        ]
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                items = await p.list_provider_credentials()
        assert items[0]["provider"] == "google"

    @pytest.mark.asyncio
    async def test_delete_sends_kind_and_key(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.delete(f"{BASE_URL}/v1/provider-credentials/tool/google").mock(
                return_value=httpx.Response(204)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.delete_provider_credentials("google")
        assert route.called


class TestSyncWrappers:
    def test_set_sync(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.put(f"{BASE_URL}/v1/provider-credentials").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "kind": "tool",
                        "provider": "google",
                        "client_id": "gid",
                        "created_at": "2026-06-06T00:00:00Z",
                        "updated_at": "2026-06-06T00:00:00Z",
                    },
                )
            )
            p = Keyhaven(BASE_URL, API_KEY)
            result = p.set_provider_credentials_sync("google", "gid", "gsecret")
        assert result["provider"] == "google"
