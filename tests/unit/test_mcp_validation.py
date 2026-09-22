"""Exercise the registered MCP boundary, not only the business dispatchers."""

from __future__ import annotations

import asyncio
import importlib
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientError
from azure.core.exceptions import ClientAuthenticationError, ServiceRequestError, ServiceResponseError
from mcp.server import ServerRequestContext
from mcp.types import CallToolRequestParams, TextContent, Tool

from src.agents.mcp_validation import validate_tool_call

_TOOLS = [
    ("researcher", "research_company", {"company_name": "Tailspin Toys"}),
    ("sharepoint", "search_documents", {"query": "Tailspin"}),
    ("sharepoint", "get_document_content", {"drive_id": "sample-drive", "item_id": "sample-item"}),
    ("report_generator", "generate_report", {"title": "Account plan", "customer_name": "Tailspin Toys"}),
    ("quota_estimator", "generate_quota_estimation_report", {"customer_name": "Tailspin Toys", "sales_rows": []}),
]


@pytest.mark.parametrize(("server_name", "tool_name", "valid"), _TOOLS)
async def test_missing_and_wrong_required_inputs_never_dispatch(
    server_name: str, tool_name: str, valid: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    context = Mock(spec=ServerRequestContext)
    definitions = await module.handle_list_tools(context, None)
    tool = next(tool for tool in definitions.tools if tool.name == tool_name)
    dispatch = AsyncMock()
    monkeypatch.setattr(module, "call_tool", dispatch)

    invalid_arguments: list[dict[str, Any] | None] = [None, {}]
    for required in tool.input_schema["required"]:
        invalid_arguments.append({key: value for key, value in valid.items() if key != required})
        for wrong in (None, 42, True, {}):
            invalid_arguments.append({**valid, required: wrong})
        if tool.input_schema["properties"][required]["type"] != "array":
            invalid_arguments.append({**valid, required: []})
    for arguments in invalid_arguments:
        result = await module.handle_call_tool(context, CallToolRequestParams(name=tool_name, arguments=arguments))
        assert result.is_error
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        assert result.content[0].text.startswith("Input validation error: ")
    dispatch.assert_not_awaited()


@pytest.mark.parametrize(("server_name", "tool_name", "valid"), _TOOLS)
async def test_unknown_tool_never_dispatches(
    server_name: str, tool_name: str, valid: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    dispatch = AsyncMock()
    monkeypatch.setattr(module, "call_tool", dispatch)
    result = await module.handle_call_tool(
        Mock(spec=ServerRequestContext), CallToolRequestParams(name="unknown", arguments=valid)
    )
    assert result.model_dump(by_alias=True, exclude_none=True) == {
        "resultType": "complete",
        "content": [{"type": "text", "text": "Unknown tool: unknown"}],
        "isError": True,
    }
    dispatch.assert_not_awaited()


@pytest.mark.parametrize(("server_name", "tool_name", "valid"), _TOOLS)
async def test_additional_properties_preserve_each_advertised_contract(
    server_name: str, tool_name: str, valid: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    dispatch = AsyncMock(return_value=[TextContent(type="text", text="ok")])
    monkeypatch.setattr(module, "call_tool", dispatch)
    arguments = {**valid, "additional_field": {"arbitrary": True}}
    result = await module.handle_call_tool(
        Mock(spec=ServerRequestContext), CallToolRequestParams(name=tool_name, arguments=arguments)
    )
    if server_name in {"report_generator", "quota_estimator"}:
        assert result.is_error
        dispatch.assert_not_awaited()
    else:
        assert not result.is_error
        dispatch.assert_awaited_once_with(tool_name, arguments)


@pytest.mark.parametrize(
    ("server_name", "tool_name", "arguments"),
    [
        ("researcher", "research_company", {"company_name": "Tailspin Toys", "focus_areas": []}),
        ("sharepoint", "search_documents", {"query": "Tailspin", "site_id": None}),
        ("report_generator", "generate_report", {"title": "Plan", "customer_name": "Tailspin", "format": "pdf"}),
        ("report_generator", "generate_report", {"title": "Plan", "customer_name": "Tailspin", "format": "DOCX"}),
        ("report_generator", "generate_report", {"title": "Plan", "customer_name": "Tailspin", "pipeline_data": [1]}),
        (
            "report_generator",
            "generate_report",
            {"title": "Plan", "customer_name": "Tailspin", "sharepoint_docs": ["x"]},
        ),
        ("report_generator", "generate_report", {"title": "Plan", "customer_name": "Tailspin", "research_data": []}),
        ("report_generator", "generate_report", {"title": "Plan", "customer_name": "Tailspin", "forecast_data": None}),
        (
            "report_generator",
            "generate_report",
            {"title": "Plan", "customer_name": "Tailspin", "additional_context": {}},
        ),
        ("quota_estimator", "generate_quota_estimation_report", {"customer_name": "Tailspin", "sales_rows": [1]}),
        *[
            (
                "quota_estimator",
                "generate_quota_estimation_report",
                {"customer_name": "Tailspin", "sales_rows": [], **invalid},
            )
            for invalid in [
                {"formats": "xlsx"},
                {"formats": ["docx"]},
                {"formats": [1]},
                {"scenario": "invalid"},
                {"data_source": "invalid"},
                {"output_dir": None},
                {"workiq_activity": []},
            ]
        ],
    ],
)
async def test_invalid_optional_nested_and_enum_inputs_never_dispatch(
    server_name: str, tool_name: str, arguments: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    dispatch = AsyncMock()
    monkeypatch.setattr(module, "call_tool", dispatch)
    result = await module.handle_call_tool(
        Mock(spec=ServerRequestContext), CallToolRequestParams(name=tool_name, arguments=arguments)
    )
    assert result.is_error
    dispatch.assert_not_awaited()


@pytest.mark.parametrize(("server_name", "tool_name", "valid"), _TOOLS)
async def test_valid_arguments_and_model_aliases(
    server_name: str, tool_name: str, valid: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    context = Mock(spec=ServerRequestContext)
    dispatch = AsyncMock(return_value=[TextContent(type="text", text='{"status": "success"}')])
    monkeypatch.setattr(module, "call_tool", dispatch)
    result = await module.handle_call_tool(context, CallToolRequestParams(name=tool_name, arguments=valid))
    dispatch.assert_awaited_once_with(tool_name, valid)
    assert result.model_dump(by_alias=True, exclude_none=True) == {
        "resultType": "complete",
        "content": [{"type": "text", "text": '{"status": "success"}'}],
        "isError": False,
    }
    tools = (await module.handle_list_tools(context, None)).model_dump(by_alias=True)
    assert all("inputSchema" in tool and "input_schema" not in tool for tool in tools["tools"])


@pytest.mark.parametrize(
    ("server_name", "tool_name", "arguments", "error"),
    [
        (
            "report_generator",
            "generate_report",
            {"title": "Plan", "customer_name": "Tailspin"},
            PermissionError("read-only output"),
        ),
        *[
            (
                "quota_estimator",
                "generate_quota_estimation_report",
                {"customer_name": "Tailspin", "sales_rows": []},
                error,
            )
            for error in (ValueError("no rows"), OSError("output unavailable"))
        ],
        *[
            ("sharepoint", "search_documents", {"query": "Tailspin"}, error)
            for error in (
                ClientError("request failed"),
                ClientAuthenticationError("authentication failed"),
                ServiceRequestError("credential request failed"),
                ServiceResponseError("credential response failed"),
                TimeoutError("request timed out"),
            )
        ],
    ],
)
async def test_known_operational_errors_are_tool_errors(
    server_name: str, tool_name: str, arguments: dict[str, Any], error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    monkeypatch.setattr(module, "call_tool", AsyncMock(side_effect=error))
    result = await module.handle_call_tool(
        Mock(spec=ServerRequestContext), CallToolRequestParams(name=tool_name, arguments=arguments)
    )
    assert result.is_error
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == str(error)


@pytest.mark.parametrize(("server_name", "tool_name", "valid"), _TOOLS)
@pytest.mark.parametrize("error", [RuntimeError("bug"), TypeError("bug"), KeyError("bug"), asyncio.CancelledError()])
async def test_programmer_faults_and_cancellation_are_not_swallowed(
    server_name: str, tool_name: str, valid: dict[str, Any], error: BaseException, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"src.agents.{server_name}.mcp_server")
    monkeypatch.setattr(module, "call_tool", AsyncMock(side_effect=error))
    with pytest.raises(type(error)):
        await module.handle_call_tool(
            Mock(spec=ServerRequestContext), CallToolRequestParams(name=tool_name, arguments=valid)
        )


def test_validation_does_not_insert_defaults_or_restrict_open_objects() -> None:
    tool = Tool(
        name="example",
        input_schema={
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "default": "base"},
                "data": {"type": "object"},
            },
        },
    )
    arguments = {"data": {"nested": [None, False, {"extra": 42}]}}
    assert validate_tool_call(CallToolRequestParams(name="example", arguments=arguments), [tool]) == arguments
    assert validate_tool_call(CallToolRequestParams(name="example"), [tool]) == {}


async def test_research_focus_remains_a_string_not_an_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.agents.researcher import mcp_server

    dispatch = AsyncMock(return_value=[TextContent(type="text", text="ok")])
    monkeypatch.setattr(mcp_server, "call_tool", dispatch)
    arguments = {"company_name": "", "focus_areas": "new focus, not a predefined enum"}
    result = await mcp_server.handle_call_tool(
        Mock(spec=ServerRequestContext), CallToolRequestParams(name="research_company", arguments=arguments)
    )
    assert not result.is_error
    dispatch.assert_awaited_once_with("research_company", arguments)


async def test_documented_mcp_example_uses_executable_sdk2_callbacks() -> None:
    path = Path(__file__).resolve().parents[2] / "website" / "docs" / "building-blocks" / "mcp.md"
    examples = re.findall(r"```python\n(.*?)\n```", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    assert len(examples) == 1
    namespace: dict[str, Any] = {"__name__": "documented_mcp_example"}
    exec(compile(examples[0], str(path), "exec"), namespace)
    context = Mock(spec=ServerRequestContext)

    definitions = await namespace["list_tools"](context, None)
    assert [tool.name for tool in definitions.tools] == ["lookup_customer"]
    valid = await namespace["call_tool"](
        context, CallToolRequestParams(name="lookup_customer", arguments={"name": "Example"})
    )
    assert not valid.is_error
    assert valid.content[0].text == "Customer: Example"
    invalid = await namespace["call_tool"](context, CallToolRequestParams(name="lookup_customer"))
    assert invalid.is_error
    assert invalid.content[0].text == "Input validation error: 'name' is a required property"
