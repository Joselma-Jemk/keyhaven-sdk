from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

from keyhaven.sdk.client import Keyhaven


def _build_tool(
    fn: dict[str, Any],
    client: Keyhaven,
    owner_id: str,
) -> BaseTool:
    try:
        from langchain_core.tools import StructuredTool
        from pydantic import create_model
    except ImportError as exc:
        raise ImportError(
            "keyhaven[langchain] extra not installed. Run: pip install 'keyhaven[langchain]'"
        ) from exc

    name = fn["qualified_name"].replace(".", "_")
    description = fn.get("description", "")
    params_schema: dict[str, Any] = fn.get("parameters_schema", {})
    properties: dict[str, Any] = params_schema.get("properties", {})
    required: list[str] = list(params_schema.get("required", []))

    fields: dict[str, Any] = {}
    for field_name, field_schema in properties.items():
        json_type = field_schema.get("type", "string")
        py_type: type[Any]
        if json_type == "string":
            py_type = str
        elif json_type == "integer":
            py_type = int
        elif json_type == "number":
            py_type = float
        elif json_type == "boolean":
            py_type = bool
        elif json_type in ("array",):
            py_type = list[Any]
        elif json_type in ("object",):
            py_type = dict[str, Any]
        else:
            py_type = str

        default: Any = ...
        if field_name not in required:
            default = None

        fields[field_name] = (py_type, default)

    args_schema = create_model(f"{name}_args", **fields)

    async def _tool_fn(**kwargs: Any) -> Any:
        return await client.execute(fn["qualified_name"], owner_id, kwargs)

    return StructuredTool(
        name=name,
        description=description,
        args_schema=args_schema,
        coroutine=_tool_fn,
    )


async def keyhaven_tools(
    client: Keyhaven,
    owner_id: str,
    *,
    apps: list[str] | None = None,
) -> list[BaseTool]:
    """Return one LangChain StructuredTool per Function from this owner's linked apps.

    If ``apps`` is provided, only Functions from those Apps are returned.
    The langchain-core dependency is imported lazily — raises a helpful ImportError
    if ``keyhaven[langchain]`` is not installed.
    """
    try:
        from langchain_core.tools import StructuredTool  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "keyhaven[langchain] extra not installed. Run: pip install 'keyhaven[langchain]'"
        ) from exc

    linked = await client.list_linked_accounts(owner_id)
    connected: set[str] = {acct["app_name"] for acct in linked}

    all_apps = await client.list_apps()

    tools: list[BaseTool] = []
    for app in all_apps:
        app_name: str = app["name"]
        if app_name not in connected:
            continue
        if apps is not None and app_name not in apps:
            continue
        for fn in app.get("functions", []):
            tools.append(_build_tool(fn, client, owner_id))
    return tools


def keyhaven_tools_sync(
    client: Keyhaven,
    owner_id: str,
    *,
    apps: list[str] | None = None,
) -> list[BaseTool]:
    """Sync version — wraps keyhaven_tools in asyncio.run."""
    import asyncio

    return asyncio.run(keyhaven_tools(client, owner_id, apps=apps))
