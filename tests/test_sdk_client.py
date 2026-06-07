from __future__ import annotations

import httpx
import pytest
import respx

from keyhaven.sdk import AuthenticationError, Keyhaven, NotFoundError, OwnerMismatchError
from keyhaven.sdk.exceptions import KeyhavenHTTPError, KeyhavenNetworkError, ProviderError

BASE_URL = "https://keyhaven.example.com"
API_KEY = "prx_test_key_abc123"


def _error_json(code: str, message: str, status: int) -> httpx.Response:
    return httpx.Response(
        status,
        json={"success": False, "error": {"code": code, "message": message}},
    )


# ----- connect


class TestConnect:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/oauth/start").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "auth_url": "https://google.com/auth?state=abc",
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                url = await p.connect("gmail", "user_1")
        assert url == "https://google.com/auth?state=abc"

    @pytest.mark.asyncio
    async def test_happy_path_with_post_redirect(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.post(f"{BASE_URL}/v1/oauth/start").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "auth_url": "https://google.com/auth?state=abc",
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.connect("gmail", "user_1", post_redirect="https://app.com/cb")
        import json

        body = json.loads(route.calls.last.request.content)
        assert body["post_redirect"] == "https://app.com/cb"

    @pytest.mark.asyncio
    async def test_error_401(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/oauth/start").mock(
                return_value=_error_json("AUTH_FAILED", "invalid key", 401)
            )
            p = Keyhaven(BASE_URL, API_KEY)
            with pytest.raises(AuthenticationError) as exc:
                await p.connect("gmail", "user_1")
        assert exc.value.status_code == 401
        assert exc.value.error_code == "AUTH_FAILED"


# ----- execute


class TestExecute:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=httpx.Response(
                    200,
                    json={"success": True, "result": {"id": "msg_1", "sent": True}},
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                result = await p.execute(
                    "gmail.send_email",
                    "user_1",
                    {"to": "a@b.com", "subject": "Hi", "body": "Hello"},
                )
        assert result == {"id": "msg_1", "sent": True}

    @pytest.mark.asyncio
    async def test_sends_api_key_header(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=httpx.Response(200, json={"success": True, "result": None})
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.execute("gmail.send_email", "user_1", {})
        assert route.calls.last.request.headers["X-API-Key"] == API_KEY

    @pytest.mark.asyncio
    async def test_error_403(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=_error_json("OWNER_MISMATCH", "not your owner", 403)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(OwnerMismatchError) as exc:
                    await p.execute("gmail.send_email", "user_2", {})
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_404(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=_error_json("NOT_FOUND", "function not found", 404)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(NotFoundError) as exc:
                    await p.execute("unknown.fn", "user_1", {})
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_error_502(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=_error_json("PROVIDER_ERROR", "gmail down", 502)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(ProviderError) as exc:
                    await p.execute("gmail.send_email", "user_1", {})
        assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_other_4xx(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=_error_json("RATE_LIMIT", "too fast", 429)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(KeyhavenHTTPError) as exc:
                    await p.execute("gmail.send_email", "user_1", {})
        assert exc.value.status_code == 429
        assert exc.value.error_code == "RATE_LIMIT"
        assert not isinstance(exc.value, AuthenticationError)
        assert not isinstance(exc.value, ProviderError)


# ----- list_apps


class TestListApps:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "apps": [
                            {
                                "name": "gmail",
                                "display_name": "Gmail",
                                "provider": "google",
                                "version": "0.1.0",
                                "description": "Gmail",
                                "scopes": ["read"],
                                "source": "native",
                                "functions": [],
                            }
                        ],
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                apps = await p.list_apps()
        assert len(apps) == 1
        assert apps[0]["name"] == "gmail"

    @pytest.mark.asyncio
    async def test_empty(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                return_value=httpx.Response(200, json={"success": True, "apps": []})
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                apps = await p.list_apps()
        assert apps == []


# ----- list_linked_accounts


class TestListLinkedAccounts:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/linked-accounts").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "linked_accounts": [
                            {
                                "id": "abc",
                                "owner_id": "user_1",
                                "app_name": "gmail",
                                "scopes": ["read"],
                                "status": "active",
                                "created_at": "2025-01-01T00:00:00",
                                "updated_at": "2025-01-01T00:00:00",
                            }
                        ],
                    },
                )
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                accounts = await p.list_linked_accounts("user_1")
        assert len(accounts) == 1
        assert accounts[0]["app_name"] == "gmail"

    @pytest.mark.asyncio
    async def test_passes_owner_id_query(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.get(f"{BASE_URL}/v1/linked-accounts").mock(
                return_value=httpx.Response(200, json={"success": True, "linked_accounts": []})
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.list_linked_accounts("custom_owner")
        assert route.calls.last.request.url.params["owner_id"] == "custom_owner"


# ----- disconnect


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.delete(f"{BASE_URL}/v1/linked-accounts/gmail").mock(
                return_value=httpx.Response(204)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                result = await p.disconnect("gmail", "user_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_passes_owner_id_query(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            route = router.delete(f"{BASE_URL}/v1/linked-accounts/gmail").mock(
                return_value=httpx.Response(204)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                await p.disconnect("gmail", "user_1")
        assert route.calls.last.request.url.params["owner_id"] == "user_1"

    @pytest.mark.asyncio
    async def test_error_404_on_disconnect(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.delete(f"{BASE_URL}/v1/linked-accounts/gmail").mock(
                return_value=_error_json("NOT_FOUND", "not linked", 404)
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(NotFoundError):
                    await p.disconnect("gmail", "user_1")


# ----- context manager


class TestContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                return_value=httpx.Response(200, json={"success": True, "apps": []})
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                apps = await p.list_apps()
                assert apps == []
            # client should be closed
            assert p._client is None

    @pytest.mark.asyncio
    async def test_works_without_context_manager(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                return_value=httpx.Response(200, json={"success": True, "apps": []})
            )
            p = Keyhaven(BASE_URL, API_KEY)
            apps = await p.list_apps()
            assert apps == []


# ----- sync wrappers


class TestSyncWrappers:
    def test_list_apps_sync(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "apps": [
                            {
                                "name": "gmail",
                                "display_name": "Gmail",
                                "provider": "google",
                                "version": "0.1.0",
                                "description": "Gmail",
                                "scopes": ["read"],
                                "source": "native",
                                "functions": [],
                            }
                        ],
                    },
                )
            )
            p = Keyhaven(BASE_URL, API_KEY)
            apps = p.list_apps_sync()
        assert len(apps) == 1
        assert apps[0]["name"] == "gmail"

    def test_connect_sync(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/oauth/start").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "success": True,
                        "auth_url": "https://google.com/auth?state=abc",
                    },
                )
            )
            p = Keyhaven(BASE_URL, API_KEY)
            url = p.connect_sync("gmail", "user_1")
        assert url == "https://google.com/auth?state=abc"

    def test_execute_sync(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{BASE_URL}/v1/execute").mock(
                return_value=httpx.Response(
                    200,
                    json={"success": True, "result": {"ok": True}},
                )
            )
            p = Keyhaven(BASE_URL, API_KEY)
            result = p.execute_sync("gmail.send_email", "user_1", {"to": "a@b.com"})
        assert result == {"ok": True}

    def test_list_linked_accounts_sync(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/linked-accounts").mock(
                return_value=httpx.Response(200, json={"success": True, "linked_accounts": []})
            )
            p = Keyhaven(BASE_URL, API_KEY)
            accounts = p.list_linked_accounts_sync("user_1")
        assert accounts == []

    def test_disconnect_sync(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.delete(f"{BASE_URL}/v1/linked-accounts/gmail").mock(
                return_value=httpx.Response(204)
            )
            p = Keyhaven(BASE_URL, API_KEY)
            result = p.disconnect_sync("gmail", "user_1")
        assert result is None

    def test_sync_propagates_errors(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                return_value=_error_json("AUTH_FAILED", "bad key", 401)
            )
            p = Keyhaven(BASE_URL, "bad_key")
            with pytest.raises(AuthenticationError):
                p.list_apps_sync()


# ----- network error


class TestNetworkError:
    @pytest.mark.asyncio
    async def test_network_error_wraps_httpx(self) -> None:
        with respx.mock(assert_all_called=True) as router:
            router.get(f"{BASE_URL}/v1/apps").mock(
                side_effect=httpx.ConnectError("connection refused")
            )
            async with Keyhaven(BASE_URL, API_KEY) as p:
                with pytest.raises(KeyhavenNetworkError) as exc:
                    await p.list_apps()
        assert "connection refused" in str(exc.value)
