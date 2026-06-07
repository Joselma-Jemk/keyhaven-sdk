from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from keyhaven.sdk.app_handle import AppHandle
    from keyhaven.sdk.apps import Apps

from keyhaven.sdk._constants import DEFAULT_ACCOUNT_ID
from keyhaven.sdk.exceptions import (
    AuthenticationError,
    ConflictError,
    KeyhavenHTTPError,
    KeyhavenNetworkError,
    KeyhavenTimeoutError,
    NotFoundError,
    OwnerMismatchError,
    ProviderError,
    RateLimitError,
    ValidationError,
)
from keyhaven.sdk.retry import DISABLED, RetryConfig, with_retry


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return

    error_code: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None

    try:
        body = response.json()
        err = body.get("error", {}) or {}
        error_code = err.get("code")
        message = err.get("message")
        details = err.get("details")
    except Exception:
        message = response.text

    status = response.status_code
    msg = message or f"HTTP {status}"

    if status == 429:
        retry_after_raw = response.headers.get("Retry-After")
        try:
            retry_after = float(retry_after_raw) if retry_after_raw else None
        except (TypeError, ValueError):
            retry_after = None
        raise RateLimitError(
            msg,
            status_code=status,
            error_code=error_code,
            details=details,
            retry_after_seconds=retry_after,
        )

    exc_cls: type[KeyhavenHTTPError]
    if status == 401:
        exc_cls = AuthenticationError
    elif status == 403:
        exc_cls = OwnerMismatchError
    elif status == 404:
        exc_cls = NotFoundError
    elif status == 409:
        exc_cls = ConflictError
    elif status == 422:
        exc_cls = ValidationError
    elif status == 502:
        exc_cls = ProviderError
    else:
        exc_cls = KeyhavenHTTPError

    raise exc_cls(
        msg,
        status_code=status,
        error_code=error_code,
        details=details,
    )


class Keyhaven:
    """Async-first HTTP client for the Keyhaven server.

    Each method also has a ``_sync`` counterpart that wraps ``asyncio.run``.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._retry = retry if retry is not None else DISABLED
        self._client: httpx.AsyncClient | None = None
        self._apps: Apps | None = None

    async def __aenter__(self) -> Keyhaven:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"X-API-Key": self._api_key},
            )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"X-API-Key": self._api_key},
        )

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an HTTP request with retry + uniform error translation."""
        client = self._get_client()
        owned = client is not self._client

        async def _do_request() -> httpx.Response:
            return await client.request(method, url, **kwargs)

        try:
            try:
                return await with_retry(_do_request, self._retry)
            except httpx.TimeoutException as exc:
                raise KeyhavenTimeoutError(str(exc)) from exc
            except httpx.RequestError as exc:
                raise KeyhavenNetworkError(str(exc)) from exc
        finally:
            if owned:
                await client.aclose()

    async def connect(
        self,
        app_name: str,
        owner_id: str,
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
        post_redirect: str | None = None,
        scopes: list[str] | None = None,
    ) -> str:
        """Initiate OAuth. Returns the URL the user must visit to consent.

        ``app_name`` may be an app (e.g. ``"gmail"``) or a provider connection key
        (e.g. ``"google"``); both resolve to the same shared provider connection, so
        one consent links every app of that provider. ``scopes`` requests a subset of
        the provider's scopes (the union across the connection's apps); ``None``
        requests the representative app's declared scopes. Previously-granted scopes
        are preserved (incremental consent).
        """
        body: dict[str, Any] = {
            "app_name": app_name,
            "owner_id": owner_id,
            "account_id": account_id,
        }
        if post_redirect is not None:
            body["post_redirect"] = post_redirect
        if scopes is not None:
            body["scopes"] = scopes

        response = await self._request("POST", "/v1/oauth/start", json=body)
        _raise_for_status(response)
        data = response.json()
        return str(data["auth_url"])

    async def execute(
        self,
        function_name: str,
        owner_id: str,
        args: dict[str, Any],
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
    ) -> Any:
        """Execute ``function_name`` (e.g. \"gmail.send_email\") on behalf of ``owner_id``."""
        response = await self._request(
            "POST",
            "/v1/execute",
            json={
                "function": function_name,
                "owner_id": owner_id,
                "account_id": account_id,
                "args": args,
            },
        )
        _raise_for_status(response)
        data = response.json()
        return data.get("result")

    async def list_apps(self) -> list[dict[str, Any]]:
        """All Apps available on this Keyhaven instance."""
        response = await self._request("GET", "/v1/apps")
        _raise_for_status(response)
        data = response.json()
        return list(data.get("apps", []))

    async def list_connections(self, owner_id: str | None = None) -> list[dict[str, Any]]:
        """Provider-grouped catalog for a 3-level Provider > App > Scopes UI.

        Each entry: ``{connection_key, provider, scopes, granted, connected, apps}``.
        ``scopes`` is the union requestable at ``connect``; with ``owner_id`` set,
        ``granted`` / ``connected`` reflect that owner's state.
        """
        params: dict[str, Any] = {}
        if owner_id is not None:
            params["owner_id"] = owner_id
        response = await self._request("GET", "/v1/connections", params=params)
        _raise_for_status(response)
        data = response.json()
        return list(data.get("connections", []))

    async def list_linked_accounts(
        self,
        owner_id: str,
        *,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Apps connected by ``owner_id``."""
        params: dict[str, Any] = {"owner_id": owner_id}
        if account_id is not None:
            params["account_id"] = account_id
        response = await self._request(
            "GET",
            "/v1/linked-accounts",
            params=params,
        )
        _raise_for_status(response)
        data = response.json()
        return list(data.get("linked_accounts", []))

    async def disconnect(
        self,
        app_name: str,
        owner_id: str,
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
    ) -> None:
        """Revoke an owner's link for ``app_name``."""
        response = await self._request(
            "DELETE",
            f"/v1/linked-accounts/{app_name}",
            params={"owner_id": owner_id, "account_id": account_id},
        )
        if response.status_code == 204:
            return
        _raise_for_status(response)

    # ----- Sync wrappers

    def connect_sync(
        self,
        app_name: str,
        owner_id: str,
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
        post_redirect: str | None = None,
        scopes: list[str] | None = None,
    ) -> str:
        return asyncio.run(
            self.connect(
                app_name,
                owner_id,
                account_id=account_id,
                post_redirect=post_redirect,
                scopes=scopes,
            )
        )

    def execute_sync(
        self,
        function_name: str,
        owner_id: str,
        args: dict[str, Any],
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
    ) -> Any:
        return asyncio.run(self.execute(function_name, owner_id, args, account_id=account_id))

    def list_apps_sync(self) -> list[dict[str, Any]]:
        return asyncio.run(self.list_apps())

    def list_connections_sync(self, owner_id: str | None = None) -> list[dict[str, Any]]:
        return asyncio.run(self.list_connections(owner_id))

    def list_linked_accounts_sync(
        self,
        owner_id: str,
        *,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return asyncio.run(self.list_linked_accounts(owner_id, account_id=account_id))

    def disconnect_sync(
        self,
        app_name: str,
        owner_id: str,
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
    ) -> None:
        return asyncio.run(self.disconnect(app_name, owner_id, account_id=account_id))

    def login_start_sync(self, provider: str, redirect_uri: str) -> str:
        return asyncio.run(self.login_start(provider, redirect_uri))

    def login_exchange_sync(self, login_token: str) -> dict[str, Any]:
        return asyncio.run(self.login_exchange(login_token))

    def app(self, name: str) -> AppHandle:
        """Return an `AppHandle` that lets you call `app.function_name(**args)`."""
        from keyhaven.sdk.app_handle import AppHandle

        return AppHandle(self, name)

    @property
    def apps(self) -> Apps:
        """Typed, namespaced accessors: `client.apps.google_calendar.events_list(...)`.

        Generated from the catalog (`scripts/gen_sdk.py`). Each method accepts a
        typed `request=` model or raw `**fields` and forwards to `execute()`.
        Additive — the dynamic `client.app(name)` API is unaffected.
        """
        from keyhaven.sdk.apps import Apps

        if self._apps is None:
            self._apps = Apps(self)
        return self._apps

    async def login_start(self, provider: str, redirect_uri: str) -> str:
        """Begin an OIDC login flow. Returns the provider auth URL to redirect the user to."""
        response = await self._request(
            "POST",
            "/v1/login/start",
            json={"provider": provider, "redirect_uri": redirect_uri},
        )
        _raise_for_status(response)
        data = response.json()
        return str(data["auth_url"])

    async def login_exchange(self, login_token: str) -> dict[str, Any]:
        """Exchange a login_token (from the broker callback) for identity claims."""
        response = await self._request(
            "POST",
            "/v1/login/exchange",
            json={"login_token": login_token},
        )
        _raise_for_status(response)
        data = response.json()
        return dict(data["claims"])

    # ----- Provider credentials (OAuth client_id / client_secret, master key only)

    async def set_provider_credentials(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        *,
        kind: str = "tool",
    ) -> dict[str, Any]:
        """Configure the deployment's OAuth client credentials for a provider.

        ``provider`` is the provider / connection slug (e.g. ``"google"``), shared
        by every app of that provider (Gmail, Calendar, …). ``kind`` is ``"tool"``
        for the tool-calling OAuth flow or ``"login"`` for the login broker (which
        falls back to the ``tool`` credential when unset). Requires a master API key.
        The secret is encrypted at rest and is never returned. Replaces any existing
        credentials for ``(kind, provider)``.
        """
        response = await self._request(
            "PUT",
            "/v1/provider-credentials",
            json={
                "kind": kind,
                "provider": provider,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        _raise_for_status(response)
        return dict(response.json())

    async def list_provider_credentials(self) -> list[dict[str, Any]]:
        """List configured provider credentials (without secrets). Master key only."""
        response = await self._request("GET", "/v1/provider-credentials")
        _raise_for_status(response)
        data = response.json()
        return list(data.get("provider_credentials", []))

    async def delete_provider_credentials(self, provider: str, *, kind: str = "tool") -> None:
        """Remove the OAuth client credentials for ``(kind, provider)``. Master key only."""
        response = await self._request("DELETE", f"/v1/provider-credentials/{kind}/{provider}")
        if response.status_code == 204:
            return
        _raise_for_status(response)

    def set_provider_credentials_sync(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        *,
        kind: str = "tool",
    ) -> dict[str, Any]:
        return asyncio.run(
            self.set_provider_credentials(provider, client_id, client_secret, kind=kind)
        )

    def list_provider_credentials_sync(self) -> list[dict[str, Any]]:
        return asyncio.run(self.list_provider_credentials())

    def delete_provider_credentials_sync(self, provider: str, *, kind: str = "tool") -> None:
        return asyncio.run(self.delete_provider_credentials(provider, kind=kind))

    async def health(self) -> dict[str, Any]:
        """Hit `/v1/health` and return the parsed JSON body. Raises on non-2xx."""
        response = await self._request("GET", "/v1/health")
        if response.status_code >= 400:
            from keyhaven.sdk.client import _raise_for_status

            _raise_for_status(response)
        result: dict[str, Any] = response.json() if response.content else {}
        return result

    def health_sync(self) -> dict[str, Any]:
        return asyncio.run(self.health())

    def execute_app_sync(
        self,
        app_name: str,
        function_name: str,
        owner_id: str,
        args: dict[str, Any] | None = None,
        *,
        account_id: str = DEFAULT_ACCOUNT_ID,
    ) -> Any:
        return asyncio.run(
            self.app(app_name).execute(
                function_name, owner_id=owner_id, args=args, account_id=account_id
            )
        )
