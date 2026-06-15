"""Unit tests for the Databricks Genie client adapter."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from src.orchestrator.databricks_genie import (
    DatabricksGenieClient,
    DatabricksGenieConfig,
    DatabricksGenieConfigurationError,
    DatabricksGenieMcpClient,
    DatabricksGenieMcpConfig,
    databricks_genie_query_func,
)


class _FakeGenie:
    def __init__(self) -> None:
        self.started: list[dict[str, str]] = []
        self.followups: list[dict[str, str]] = []
        self.result_calls: list[dict[str, str]] = []

    def start_conversation_and_wait(self, **kwargs: str) -> SimpleNamespace:
        self.started.append(kwargs)
        return SimpleNamespace(
            conversation_id="conversation-1",
            message_id="message-1",
            attachments=[SimpleNamespace(attachment_id="attachment-1")],
            content="Here are the rows.",
        )

    def create_message_and_wait(self, **kwargs: str) -> SimpleNamespace:
        self.followups.append(kwargs)
        return SimpleNamespace(
            message_id="message-2",
            attachments=[SimpleNamespace(attachment_id="attachment-2")],
        )

    def get_message_query_result(self, **kwargs: str) -> SimpleNamespace:
        self.result_calls.append(kwargs)
        return SimpleNamespace(
            statement_response=SimpleNamespace(
                result=SimpleNamespace(
                    data_array=[["Northwest", "Toys", "2026-01-01", 123.45, 5]],
                    schema=SimpleNamespace(
                        columns=[
                            SimpleNamespace(name="sales_territory"),
                            SimpleNamespace(name="productCategory"),
                            SimpleNamespace(name="orderDate"),
                            SimpleNamespace(name="net_sales_amount"),
                            SimpleNamespace(name="units_sold"),
                        ]
                    ),
                )
            )
        )


class _FakeWorkspace:
    def __init__(self) -> None:
        self.genie = _FakeGenie()


def test_config_loads_from_env() -> None:
    env = {
        "DATABRICKS_WORKSPACE_URL": "https://adb-123.azuredatabricks.net/",
        "DATABRICKS_GENIE_SPACE_ID": "space-123",
        "DATABRICKS_WAREHOUSE_ID": "warehouse-123",
    }
    with patch.dict("os.environ", env, clear=True):
        config = DatabricksGenieConfig.from_env()

    assert config.workspace_url == "https://adb-123.azuredatabricks.net"
    assert config.space_id == "space-123"
    assert config.warehouse_id == "warehouse-123"


def test_config_requires_workspace_and_space() -> None:
    with patch.dict("os.environ", {}, clear=True), pytest.raises(DatabricksGenieConfigurationError) as exc_info:
        DatabricksGenieConfig.from_env()

    assert "DATABRICKS_WORKSPACE_URL" in str(exc_info.value)
    assert "DATABRICKS_GENIE_SPACE_ID" in str(exc_info.value)


def test_query_starts_conversation_and_normalizes_rows() -> None:
    workspace = _FakeWorkspace()
    client = DatabricksGenieClient(
        DatabricksGenieConfig(
            workspace_url="https://adb-123.azuredatabricks.net",
            space_id="space-123",
        ),
        workspace_client=workspace,
    )

    result = client.query("Show sales by territory")

    assert result["status"] == "ok"
    assert result["conversation_id"] == "conversation-1"
    assert result["row_count"] == 1
    rows = result["rows"]
    assert isinstance(rows, list)
    assert rows[0]["sales_territory"] == "Northwest"
    assert rows[0]["source_platform"] == "databricks"
    assert workspace.genie.started[0]["space_id"] == "space-123"
    assert workspace.genie.result_calls[0]["attachment_id"] == "attachment-1"


def test_query_supports_followup_conversation() -> None:
    workspace = _FakeWorkspace()
    client = DatabricksGenieClient(
        DatabricksGenieConfig(
            workspace_url="https://adb-123.azuredatabricks.net",
            space_id="space-123",
        ),
        workspace_client=workspace,
    )

    result = client.query("Break that down by product", conversation_id="conversation-1")

    assert result["message_id"] == "message-2"
    assert workspace.genie.followups[0]["conversation_id"] == "conversation-1"
    assert workspace.genie.started == []


def test_tool_handler_returns_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABRICKS_WORKSPACE_URL", raising=False)
    monkeypatch.delenv("DATABRICKS_HOST", raising=False)
    monkeypatch.delenv("DATABRICKS_GENIE_SPACE_ID", raising=False)
    monkeypatch.delenv("DATABRICKS_GENIE_MCP_URL", raising=False)

    result = databricks_genie_query_func({"question": "sales"})

    assert result["status"] == "configuration_error"
    assert result["required_environment"] == ["DATABRICKS_WORKSPACE_URL", "DATABRICKS_GENIE_SPACE_ID"]


def test_inline_mapping_rows_are_preserved() -> None:
    workspace = _FakeWorkspace()
    workspace.genie.start_conversation_and_wait = lambda **_kwargs: SimpleNamespace(
        conversation_id="conversation-1",
        message_id="message-1",
        attachments=[SimpleNamespace(query_result=[{"sales_territory": "Southwest", "units_sold": 7}])],
    )
    client = DatabricksGenieClient(
        DatabricksGenieConfig(workspace_url="https://adb-123.azuredatabricks.net", space_id="space-123"),
        workspace_client=workspace,
    )

    result: dict[str, Any] = client.query("sales")

    rows = result["rows"]
    assert isinstance(rows, list)
    assert rows == [{"sales_territory": "Southwest", "units_sold": 7, "source_platform": "databricks"}]


class _FakeMcpTool:
    def __init__(self, name: str, properties: dict[str, Any] | None = None, description: str = "") -> None:
        self.name = name
        self.description = description
        self.inputSchema = {"type": "object", "properties": properties or {}}


class _FakeMcpResponse:
    def __init__(self, text: str) -> None:
        self.content = [SimpleNamespace(type="text", text=text)]


class _FakeMcpClient:
    def __init__(self, tools: list[_FakeMcpTool], response_text: str) -> None:
        self._tools = tools
        self._response_text = response_text
        self.calls: list[dict[str, Any]] = []

    def list_tools(self) -> list[_FakeMcpTool]:
        return self._tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> _FakeMcpResponse:
        self.calls.append({"name": name, "arguments": arguments})
        return _FakeMcpResponse(self._response_text)


def test_mcp_config_from_env_derives_workspace_host() -> None:
    env = {"DATABRICKS_GENIE_MCP_URL": "https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9/"}
    with patch.dict("os.environ", env, clear=True):
        config = DatabricksGenieMcpConfig.from_env()

    assert config.mcp_url == "https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9"
    assert config.workspace_url == "https://adb-9.azuredatabricks.net"


def test_mcp_config_requires_https_url() -> None:
    env = {"DATABRICKS_GENIE_MCP_URL": "http://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9"}
    with patch.dict("os.environ", env, clear=True), pytest.raises(DatabricksGenieConfigurationError):
        DatabricksGenieMcpConfig.from_env()


def test_mcp_client_queries_and_normalizes_json_rows() -> None:
    tool = _FakeMcpTool(
        "query_genie_space",
        properties={"query": {"type": "string", "description": "natural language question"}},
    )
    payload = json.dumps(
        [
            {"sales_territory": "Northwest", "net_sales_amount": 100.0},
            {"sales_territory": "Southwest", "net_sales_amount": 200.0},
        ]
    )
    mcp_client = _FakeMcpClient([tool], payload)
    client = DatabricksGenieMcpClient(
        DatabricksGenieMcpConfig(mcp_url="https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9"),
        mcp_client=mcp_client,
    )

    result = client.query("Show sales by territory")

    assert result["status"] == "ok"
    assert result["transport"] == "managed-mcp"
    assert result["tool_name"] == "query_genie_space"
    assert result["row_count"] == 2
    rows = result["rows"]
    assert isinstance(rows, list)
    assert rows[0]["sales_territory"] == "Northwest"
    assert rows[0]["source_platform"] == "databricks"
    assert mcp_client.calls[0] == {"name": "query_genie_space", "arguments": {"query": "Show sales by territory"}}


def test_mcp_client_handles_statement_response_payload() -> None:
    tool = _FakeMcpTool("genie", properties={"question": {"type": "string"}})
    payload = json.dumps(
        {
            "statement_response": {
                "result": {"data_array": [["Northwest", 5]]},
                "manifest": {"schema": {"columns": [{"name": "territory"}, {"name": "units"}]}},
            }
        }
    )
    mcp_client = _FakeMcpClient([tool], payload)
    client = DatabricksGenieMcpClient(
        DatabricksGenieMcpConfig(mcp_url="https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9"),
        mcp_client=mcp_client,
    )

    result = client.query("totals")

    assert mcp_client.calls[0]["arguments"] == {"question": "totals"}
    rows = result["rows"]
    assert isinstance(rows, list)
    assert rows == [{"territory": "Northwest", "units": 5, "source_platform": "databricks"}]


def test_mcp_client_raises_when_no_tools() -> None:
    mcp_client = _FakeMcpClient([], "")
    client = DatabricksGenieMcpClient(
        DatabricksGenieMcpConfig(mcp_url="https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9"),
        mcp_client=mcp_client,
    )

    with pytest.raises(Exception):
        client.query("anything")


def test_tool_handler_uses_mcp_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABRICKS_GENIE_MCP_URL", "https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9")
    tool = _FakeMcpTool("genie_query", properties={"query": {"type": "string"}})
    mcp_client = _FakeMcpClient([tool], json.dumps([{"territory": "Northwest"}]))

    captured: dict[str, Any] = {}

    def _fake_from_env() -> DatabricksGenieMcpClient:
        client = DatabricksGenieMcpClient(
            DatabricksGenieMcpConfig(mcp_url="https://adb-9.azuredatabricks.net/api/2.0/mcp/genie/space-9"),
            mcp_client=mcp_client,
        )
        captured["client"] = client
        return client

    monkeypatch.setattr(DatabricksGenieMcpClient, "from_env", staticmethod(_fake_from_env))

    result = databricks_genie_query_func({"question": "sales by territory"})

    assert result["status"] == "ok"
    assert result["transport"] == "managed-mcp"
    assert "client" in captured
    assert mcp_client.calls[0]["arguments"] == {"query": "sales by territory"}
