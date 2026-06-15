"""Unit tests for the Databricks Genie client adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from src.orchestrator.databricks_genie import (
    DatabricksGenieClient,
    DatabricksGenieConfig,
    DatabricksGenieConfigurationError,
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
