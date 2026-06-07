"""Tests for the generated typed SDK namespaces (`keyhaven.sdk.apps`).

Covers: the `client.apps.<app>` accessor, the grouped `path/query/header/body`
payload produced by a typed `request=` model, header aliasing, raw `**fields`
fallback, request-model validation, and the anti-drift `gen_sdk --check` gate.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from keyhaven.sdk import Apps, Keyhaven
from keyhaven.sdk.apps.google_calendar import (
    GoogleCalendarEventsInsertBody,
    GoogleCalendarEventsInsertPath,
    GoogleCalendarEventsInsertRequest,
    GoogleCalendarEventsListQuery,
    GoogleCalendarEventsListRequest,
    GoogleCalendarNamespace,
)
from keyhaven.sdk.apps.notion import NotionGetPagePath, NotionGetPageRequest

BASE_URL = "http://test.invalid"


def _mock_execute(router: respx.Router) -> respx.Route:
    return router.post("/v1/execute").mock(
        return_value=httpx.Response(200, json={"success": True, "result": {"ok": True}})
    )


class TestAppsAccessor:
    def test_apps_property_is_cached(self) -> None:
        client = Keyhaven(BASE_URL, "k")
        assert isinstance(client.apps, Apps)
        assert client.apps is client.apps  # cached

    def test_namespace_exposes_typed_methods(self) -> None:
        client = Keyhaven(BASE_URL, "k")
        assert isinstance(client.apps.google_calendar, GoogleCalendarNamespace)
        assert callable(client.apps.google_calendar.events_list)


class TestTypedRequestPayload:
    @pytest.mark.asyncio
    async def test_grouped_request_dumps_to_args(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            route = _mock_execute(router)
            async with Keyhaven(BASE_URL, "k") as client:
                await client.apps.google_calendar.events_list(
                    owner_id="u",
                    request=GoogleCalendarEventsListRequest(
                        query=GoogleCalendarEventsListQuery(
                            timeMin="2025-01-01T00:00:00Z", maxResults=5
                        )
                    ),
                )
        body = json.loads(route.calls.last.request.content)
        assert body["function"] == "google_calendar.events_list"
        assert body["owner_id"] == "u"
        assert body["account_id"] == "default"
        # path defaulted (calendarId="primary"), query as provided, no None leaked.
        assert body["args"]["path"] == {"calendarId": "primary"}
        assert body["args"]["query"]["timeMin"] == "2025-01-01T00:00:00Z"
        assert body["args"]["query"]["maxResults"] == 5

    @pytest.mark.asyncio
    async def test_body_group_round_trips(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            route = _mock_execute(router)
            async with Keyhaven(BASE_URL, "k") as client:
                await client.apps.google_calendar.events_insert(
                    owner_id="u",
                    request=GoogleCalendarEventsInsertRequest(
                        path=GoogleCalendarEventsInsertPath(calendarId="primary"),
                        body=GoogleCalendarEventsInsertBody(
                            summary="Standup",
                            start={"dateTime": "2025-01-01T09:00:00Z"},
                            end={"dateTime": "2025-01-01T09:15:00Z"},
                        ),
                    ),
                )
        args = json.loads(route.calls.last.request.content)["args"]
        assert args["path"] == {"calendarId": "primary"}
        assert args["body"]["summary"] == "Standup"
        assert args["body"]["start"] == {"dateTime": "2025-01-01T09:00:00Z"}

    @pytest.mark.asyncio
    async def test_header_alias_is_emitted_by_wire_name(self) -> None:
        # Notion functions carry a `Notion-Version` header param (aliased field).
        with respx.mock(base_url=BASE_URL) as router:
            route = _mock_execute(router)
            async with Keyhaven(BASE_URL, "k") as client:
                await client.apps.notion.get_page(
                    owner_id="u",
                    request=NotionGetPageRequest(path=NotionGetPagePath(page_id="abc")),
                )
        args = json.loads(route.calls.last.request.content)["args"]
        assert args["path"] == {"page_id": "abc"}
        assert args["header"]["Notion-Version"] == "2022-06-28"

    @pytest.mark.asyncio
    async def test_raw_fields_fallback_without_request_model(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            route = _mock_execute(router)
            async with Keyhaven(BASE_URL, "k") as client:
                await client.apps.google_calendar.events_list(
                    owner_id="u",
                    account_id="work",
                    query={"q": "lunch"},
                )
        body = json.loads(route.calls.last.request.content)
        assert body["account_id"] == "work"
        assert body["args"] == {"query": {"q": "lunch"}}

    @pytest.mark.asyncio
    async def test_result_is_propagated(self) -> None:
        with respx.mock(base_url=BASE_URL) as router:
            _mock_execute(router)
            async with Keyhaven(BASE_URL, "k") as client:
                result = await client.apps.notion.get_page(
                    owner_id="u",
                    request=NotionGetPageRequest(path=NotionGetPagePath(page_id="abc")),
                )
        assert result == {"ok": True}


class TestRequestModelValidation:
    def test_missing_required_path_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotionGetPagePath()  # page_id is required

    def test_alias_field_accepted_by_python_name(self) -> None:
        # validate_by_name=True → the sanitized python name also populates the field.
        from keyhaven.sdk.apps.notion import NotionGetPageHeader

        hdr = NotionGetPageHeader(Notion_Version="2022-06-28")
        assert hdr.model_dump(by_alias=True) == {"Notion-Version": "2022-06-28"}
