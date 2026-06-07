from __future__ import annotations

import httpx
import pytest
import respx

from keyhaven.sdk import Keyhaven

BASE_URL = "https://keyhaven.example.com"
API_KEY = "prx_test_key_abc123"

_PAYLOAD = {
    "connections": [
        {
            "connection_key": "google",
            "provider": "Google",
            "scopes": ["https://www.googleapis.com/auth/gmail.send"],
            "granted": [],
            "connected": False,
            "apps": [
                {"name": "gmail", "functions": [{"name": "send_email", "required_scopes": []}]}
            ],
        }
    ]
}


class TestListConnections:
    @pytest.mark.asyncio
    async def test_without_owner(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.get(f"{BASE_URL}/v1/connections").mock(
                return_value=httpx.Response(200, json=_PAYLOAD)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                conns = await p.list_connections()
        assert conns[0]["connection_key"] == "google"
        assert "owner_id" not in route.calls.last.request.url.params

    @pytest.mark.asyncio
    async def test_with_owner_passes_param(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.get(f"{BASE_URL}/v1/connections").mock(
                return_value=httpx.Response(200, json=_PAYLOAD)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.list_connections("u1")
        assert route.calls.last.request.url.params["owner_id"] == "u1"

    def test_sync_wrapper(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/connections").mock(
                return_value=httpx.Response(200, json=_PAYLOAD)
            )
            p = Keyhaven(BASE_URL, API_KEY)
            conns = p.list_connections_sync("u1")
        assert conns[0]["provider"] == "Google"
