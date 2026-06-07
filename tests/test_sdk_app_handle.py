"""Tests for `keyhaven.sdk.app_handle.AppHandle`."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from keyhaven.sdk import AppHandle, Keyhaven

BASE_URL = "http://test.invalid"


class TestAppHandle:
    @pytest.mark.asyncio
    async def test_app_returns_handle(self) -> None:
        async with Keyhaven(BASE_URL, "k") as client:
            handle = client.app("gmail")
        assert isinstance(handle, AppHandle)
        assert handle.app_name == "gmail"

    @pytest.mark.asyncio
    async def test_handle_execute_explicit_form_calls_execute_with_qualified_name(
        self,
    ) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post("/v1/execute").mock(
                return_value=httpx.Response(200, json={"success": True, "result": None})
            )
            async with Keyhaven(BASE_URL, "k") as client:
                handle = client.app("gmail")
                await handle.execute("send_email", owner_id="u", args={"to": "x"})
        body = json.loads(route.calls.last.request.content)
        assert body == {
            "function": "gmail.send_email",
            "owner_id": "u",
            "account_id": "default",
            "args": {"to": "x"},
        }

    @pytest.mark.asyncio
    async def test_handle_dynamic_attribute_builds_correct_call(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post("/v1/execute").mock(
                return_value=httpx.Response(200, json={"success": True, "result": None})
            )
            async with Keyhaven(BASE_URL, "k") as client:
                handle = client.app("gmail")
                await handle.send_email(owner_id="u", to="x", subject="y", body="z")
        body = json.loads(route.calls.last.request.content)
        assert body == {
            "function": "gmail.send_email",
            "owner_id": "u",
            "account_id": "default",
            "args": {"to": "x", "subject": "y", "body": "z"},
        }

    @pytest.mark.asyncio
    async def test_handle_dynamic_attribute_propagates_server_result(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/v1/execute").mock(
                return_value=httpx.Response(200, json={"success": True, "result": {"id": "msg-1"}})
            )
            async with Keyhaven(BASE_URL, "k") as client:
                handle = client.app("gmail")
                result = await handle.send_email(owner_id="u", to="x")
        assert result == {"id": "msg-1"}

    @pytest.mark.asyncio
    async def test_dunder_attributes_raise_attributeerror(self) -> None:
        async with Keyhaven(BASE_URL, "k") as client:
            handle = client.app("gmail")
        with pytest.raises(AttributeError):
            _ = handle._private  # type: ignore[attr-defined]
        # app_name is a real property, not a coroutine
        assert handle.app_name == "gmail"

    @pytest.mark.asyncio
    async def test_handle_execute_without_args(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post("/v1/execute").mock(
                return_value=httpx.Response(200, json={"success": True, "result": None})
            )
            async with Keyhaven(BASE_URL, "k") as client:
                handle = client.app("gmail")
                await handle.execute("ping", owner_id="u")
        body = json.loads(route.calls.last.request.content)
        assert body == {
            "function": "gmail.ping",
            "owner_id": "u",
            "account_id": "default",
            "args": {},
        }

    @pytest.mark.asyncio
    async def test_handle_function_name_in_qualname(self) -> None:
        async with Keyhaven(BASE_URL, "k") as client:
            handle = client.app("gmail")
        method = handle.send_email
        assert "gmail" in method.__qualname__
        assert "send_email" in method.__qualname__


class TestAppHandleSync:
    def test_execute_app_sync(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/v1/execute").mock(
                return_value=httpx.Response(200, json={"success": True, "result": {"sent": True}})
            )
            client = Keyhaven(BASE_URL, "k")
            result = client.execute_app_sync("gmail", "send_email", "u", {"to": "x"})
        assert result == {"sent": True}
