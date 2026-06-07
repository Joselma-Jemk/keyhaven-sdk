from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from keyhaven.sdk.client import Keyhaven
from keyhaven.sdk.langchain import keyhaven_tools, keyhaven_tools_sync

LINKED_ACCOUNTS = {
    "user_1": [
        {"app_name": "gmail"},
        {"app_name": "google_calendar"},
    ]
}

APPS_LIST = [
    {
        "name": "gmail",
        "display_name": "Gmail",
        "provider": "google",
        "version": "0.1.0",
        "description": "Gmail",
        "scopes": ["read"],
        "source": "native",
        "functions": [
            {
                "name": "send_email",
                "qualified_name": "gmail.send_email",
                "description": "Send an email via Gmail.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient"},
                        "subject": {"type": "string", "description": "Subject"},
                        "body": {"type": "string", "description": "Body"},
                    },
                    "required": ["to", "subject", "body"],
                },
                "returns_schema": {"type": "object"},
            },
            {
                "name": "search_emails",
                "qualified_name": "gmail.search_emails",
                "description": "Search Gmail messages.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
                "returns_schema": {"type": "array"},
            },
        ],
    },
    {
        "name": "google_calendar",
        "display_name": "Google Calendar",
        "provider": "google",
        "version": "0.1.0",
        "description": "Calendar",
        "scopes": ["read"],
        "source": "native",
        "functions": [
            {
                "name": "list_events",
                "qualified_name": "google_calendar.list_events",
                "description": "List calendar events.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "max_results": {"type": "integer"},
                    },
                    "required": [],
                },
                "returns_schema": {"type": "array"},
            }
        ],
    },
    {
        "name": "slack",
        "display_name": "Slack",
        "provider": "slack",
        "version": "0.1.0",
        "description": "Slack",
        "scopes": ["read"],
        "source": "native",
        "functions": [],
    },
]


class _MockKeyhaven(Keyhaven):
    """A Keyhaven client that returns canned data without HTTP calls."""

    def __init__(self) -> None:
        super().__init__("http://fake", "key")
        self._execute_mock = AsyncMock()

    async def list_linked_accounts(  # type: ignore[override]
        self, owner_id: str
    ) -> list[dict[str, Any]]:
        return LINKED_ACCOUNTS.get(owner_id, [])

    async def list_apps(self) -> list[dict[str, Any]]:
        return APPS_LIST

    async def execute(  # type: ignore[override]
        self, function_name: str, owner_id: str, args: dict[str, Any]
    ) -> Any:
        return await self._execute_mock(function_name, owner_id, args)


@pytest.fixture
def mock_client() -> _MockKeyhaven:
    return _MockKeyhaven()


class TestKeyhavenTools:
    @pytest.mark.asyncio
    async def test_returns_tool_objects(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "user_1")
        assert len(tools) == 3

    @pytest.mark.asyncio
    async def test_tool_names_have_no_dots(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "user_1")
        names = {t.name for t in tools}
        assert "gmail_send_email" in names
        assert "gmail_search_emails" in names
        assert "google_calendar_list_events" in names

    @pytest.mark.asyncio
    async def test_tool_has_description(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "user_1")
        gmail_send = {t.name: t for t in tools}["gmail_send_email"]
        assert gmail_send.description == "Send an email via Gmail."

    @pytest.mark.asyncio
    async def test_tool_invocation_calls_execute(self, mock_client: _MockKeyhaven) -> None:
        mock_client._execute_mock.return_value = {"id": "msg_1", "sent": True}
        tools = await keyhaven_tools(mock_client, "user_1")
        gmail_send = {t.name: t for t in tools}["gmail_send_email"]
        result = await gmail_send.coroutine(to="a@b.com", subject="Hi", body="Hello")
        assert result == {"id": "msg_1", "sent": True}
        mock_client._execute_mock.assert_awaited_once_with(
            "gmail.send_email", "user_1", {"to": "a@b.com", "subject": "Hi", "body": "Hello"}
        )

    @pytest.mark.asyncio
    async def test_filter_by_apps(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "user_1", apps=["gmail"])
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "gmail_send_email" in names
        assert "gmail_search_emails" in names
        assert "google_calendar_list_events" not in names

    @pytest.mark.asyncio
    async def test_empty_linked_accounts(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "unknown_user")
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_tool_args_schema_is_pydantic_model(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "user_1")
        gmail_send = {t.name: t for t in tools}["gmail_send_email"]
        schema = gmail_send.args_schema.model_json_schema()
        props = schema.get("properties", {})
        assert "to" in props
        assert props["to"]["type"] == "string"
        required = schema.get("required", [])
        assert "to" in required
        assert "subject" in required
        assert "body" in required

    @pytest.mark.asyncio
    async def test_optional_args_not_required(self, mock_client: _MockKeyhaven) -> None:
        tools = await keyhaven_tools(mock_client, "user_1")
        search = {t.name: t for t in tools}["gmail_search_emails"]
        schema = search.args_schema.model_json_schema()
        required = schema.get("required", [])
        assert "max_results" not in required

    def test_sync_version(self, mock_client: _MockKeyhaven) -> None:
        tools = keyhaven_tools_sync(mock_client, "user_1")
        assert len(tools) == 3


class TestMissingLangchain:
    @pytest.mark.asyncio
    async def test_import_error_when_missing(self) -> None:
        # Simulate langchain_core being unavailable
        import sys

        saved = sys.modules.pop("langchain_core", None)
        saved_tools = sys.modules.pop("langchain_core.tools", None)
        # We need langchain_core.tools to be missing but pydantic stays
        try:
            sys.modules["langchain_core"] = None  # type: ignore[assignment]
            with pytest.raises(ImportError) as exc:
                await keyhaven_tools(
                    _MockKeyhaven(),
                    "user_1",
                )
            assert "keyhaven[langchain]" in str(exc.value)
        finally:
            if saved is not None:
                sys.modules["langchain_core"] = saved
            else:
                sys.modules.pop("langchain_core", None)
            if saved_tools is not None:
                sys.modules["langchain_core.tools"] = saved_tools
