"""Ergonomic per-App wrapper around the `Keyhaven` client.

Lets callers write `client.app("gmail").send_email(owner_id="u", to=...)` instead
of `client.execute("gmail.send_email", "u", {"to": ...})`.

The wrapper does not pre-validate function names. It builds the qualified name
"<app_name>.<function_name>" and forwards args to `Keyhaven.execute()`. Unknown
functions surface as a NotFoundError at execute time (server-side).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from keyhaven.sdk.client import Keyhaven

from keyhaven.sdk._constants import DEFAULT_ACCOUNT_ID


class AppHandle:
    """Ergonomic accessor for one app's functions. Yielded by `Keyhaven.app(name)`."""

    def __init__(self, client: Keyhaven, app_name: str) -> None:
        self._client = client
        self._app_name = app_name

    @property
    def app_name(self) -> str:
        return self._app_name

    async def execute(
        self,
        function_name: str,
        *,
        owner_id: str,
        args: dict[str, Any] | None = None,
        account_id: str = DEFAULT_ACCOUNT_ID,
    ) -> Any:
        """Explicit form: `await gmail.execute("send_email", owner_id=..., args={...})`."""
        return await self._client.execute(
            function_name=f"{self._app_name}.{function_name}",
            owner_id=owner_id,
            args=args or {},
            account_id=account_id,
        )

    def __getattr__(self, name: str) -> Callable[..., Awaitable[Any]]:
        """Dynamic ergonomic form: `await gmail.send_email(owner_id=..., **fields)`.

        Returns an async closure that calls `self.execute(name, owner_id=..., args=fields)`.
        Anything starting with `_` or matching `app_name` is excluded so the caller
        gets a normal AttributeError.
        """
        if name.startswith("_") or name in {"app_name", "execute"}:
            raise AttributeError(name)

        async def _call(
            *,
            owner_id: str,
            account_id: str = DEFAULT_ACCOUNT_ID,
            **fields: Any,
        ) -> Any:
            return await self.execute(
                name,
                owner_id=owner_id,
                args=dict(fields),
                account_id=account_id,
            )

        _call.__name__ = name
        _call.__qualname__ = f"AppHandle({self._app_name}).{name}"
        return _call
